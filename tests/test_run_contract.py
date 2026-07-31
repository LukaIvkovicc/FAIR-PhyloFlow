from __future__ import annotations

import json
import socket
from pathlib import Path

from fair_phyloflow.concatenate import concatenate_alignments
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.run_contract import (
    TaskSpec,
    _normalize_concordance,
    build_run_plan,
    execute_run_plan,
    validate_iqtree_version,
    validate_tree,
    write_run_plan,
)


def _fake_iqtree(path: Path, version: str = "2.2.2") -> Path:
    path.write_text(
        f"""#!/usr/bin/env python3
import pathlib
import sys

args = sys.argv[1:]
if "-version" in args:
    print("IQ-TREE multicore version {version}")
    raise SystemExit(0)

prefix = pathlib.Path(args[args.index("--prefix") + 1])
prefix.parent.mkdir(parents=True, exist_ok=True)
if "--gcf" in args or "--scf" in args:
    metric = "gCF" if "--gcf" in args else "sCF"
    (pathlib.Path(str(prefix) + ".cf.tree")).write_text("(a,b,c);\\n")
    (pathlib.Path(str(prefix) + ".cf.branch")).write_text("(a,b,c);\\n")
    (pathlib.Path(str(prefix) + ".cf.stat")).write_text(f"ID\\t{{metric}}\\n1\\t75.0\\n")
else:
    alignment = pathlib.Path(args[args.index("-s") + 1])
    taxa = [line[1:].strip().split()[0] for line in alignment.read_text().splitlines() if line.startswith(">")]
    tree = "(" + ",".join(f"{{taxon}}:0.1" for taxon in taxa) + ");\\n"
    pathlib.Path(str(prefix) + ".treefile").write_text(tree)
    pathlib.Path(str(prefix) + ".iqtree").write_text("Best-fit model: GTR+G\\n")
""",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def _plan_fixture(tmp_path: Path) -> tuple[WorkflowConfig, object]:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    cfg.project.outdir = tmp_path / "results"
    cfg.execution.iqtree_bin = str(_fake_iqtree(tmp_path / "iqtree2"))
    selected = sorted(Path("examples/demo_project/alignments").glob("*.fa"))
    run_dir = cfg.project.outdir / "08_runs" / "test-run"
    concatenated = run_dir / "inputs" / "concatenated.fasta"
    concatenate_alignments(Path("examples/demo_project/alignments"), concatenated, loci_paths=selected)
    plan = build_run_plan(
        cfg,
        config_path=Path("examples/demo_project/project.yaml"),
        run_dir=run_dir,
        concatenated_alignment=concatenated,
        selected_loci=selected,
    )
    return cfg, plan


def test_build_plan_has_complete_route_and_stable_fingerprint(tmp_path: Path) -> None:
    _cfg, plan = _plan_fixture(tmp_path)
    kinds = [task.kind for task in plan.tasks]
    assert kinds[0] == "iqtree_reference"
    assert kinds.count("iqtree_gene_tree") == 3
    assert kinds[-4:] == ["combine_gene_trees", "iqtree_gcf", "iqtree_scf", "normalize_concordance"]
    assert len(plan.fingerprint) == 64

    plan_path = write_run_plan(plan, Path(plan.run_dir) / "run-plan.json")
    first = plan_path.read_text(encoding="utf-8")
    write_run_plan(plan, plan_path)
    assert plan_path.read_text(encoding="utf-8") == first


def test_execute_complete_route_and_resume_verified_tasks(tmp_path: Path) -> None:
    cfg, plan = _plan_fixture(tmp_path)
    summary = execute_run_plan(plan, cfg)
    assert summary.status == "complete"
    state = json.loads(Path(summary.state_path).read_text(encoding="utf-8"))
    assert state["status"] == "complete"
    assert all(task["status"] == "verified" for task in state["tasks"].values())
    combined = Path(plan.run_dir) / "outputs" / "gene_trees.nwk"
    assert len(combined.read_text(encoding="utf-8").splitlines()) == 3
    branch_summary = Path(plan.run_dir) / "outputs" / "concordance" / "branch-summary.tsv"
    assert branch_summary.read_text(encoding="utf-8").splitlines()[0] == "ID\tgCF\tsCF"

    log = Path(plan.run_dir) / "logs" / "reference_tree.log"
    initial_mtime = log.stat().st_mtime_ns
    resumed = execute_run_plan(plan, cfg)
    assert resumed.status == "complete"
    assert log.stat().st_mtime_ns == initial_mtime


def test_changed_verified_output_recursively_invalidates_dependents(tmp_path: Path) -> None:
    cfg, plan = _plan_fixture(tmp_path)
    assert execute_run_plan(plan, cfg).status == "complete"

    reference = Path(plan.run_dir) / "outputs" / "reference" / "concatenated.treefile"
    reference.write_text(reference.read_text(encoding="utf-8").replace(":0.1", ":0.2"), encoding="utf-8")
    resumed = execute_run_plan(plan, cfg)
    assert resumed.status == "failed"
    assert "recursively invalidated" in resumed.message
    state = json.loads(Path(resumed.state_path).read_text(encoding="utf-8"))
    assert state["tasks"]["reference_tree"]["status"] == "invalid_output"
    assert state["tasks"]["gene_concordance"]["status"] == "blocked"
    assert state["tasks"]["site_concordance"]["status"] == "blocked"
    assert state["tasks"]["normalize_concordance"]["status"] == "blocked"


def test_changed_planned_input_recursively_invalidates_route(tmp_path: Path) -> None:
    cfg, plan = _plan_fixture(tmp_path)
    concatenated = Path(plan.tasks[0].inputs[0])
    concatenated.write_text(concatenated.read_text(encoding="utf-8").replace("A", "T", 1), encoding="utf-8")

    summary = execute_run_plan(plan, cfg)
    assert summary.status == "failed"
    assert "immutable plan" in summary.message.lower()
    state = json.loads(Path(summary.state_path).read_text(encoding="utf-8"))
    assert state["tasks"]["reference_tree"]["status"] == "invalid_output"
    assert state["tasks"]["gene_concordance"]["status"] == "blocked"
    assert state["tasks"]["site_concordance"]["status"] == "invalid_output"
    assert state["tasks"]["normalize_concordance"]["status"] == "blocked"


def test_run_lock_blocks_competing_executor(tmp_path: Path) -> None:
    cfg, plan = _plan_fixture(tmp_path)
    lock = Path(plan.run_dir) / ".run.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text('{"pid": 42, "hostname": "other", "created_at_utc": "now"}\n', encoding="utf-8")
    summary = execute_run_plan(plan, cfg)
    assert summary.status == "blocked"
    assert summary.reason == "run_lock"
    assert "pid=42" in summary.message


def test_stale_same_host_run_lock_is_recovered(tmp_path: Path) -> None:
    cfg, plan = _plan_fixture(tmp_path)
    lock = Path(plan.run_dir) / ".run.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(
        json.dumps({"pid": 999_999_999, "hostname": socket.gethostname(), "created_at_utc": "now"}) + "\n",
        encoding="utf-8",
    )
    summary = execute_run_plan(plan, cfg)
    assert summary.status == "complete"
    assert not lock.exists()


def test_incompatible_iqtree_is_blocked(tmp_path: Path) -> None:
    binary = _fake_iqtree(tmp_path / "iqtree2", version="3.1.0")
    compatible, message = validate_iqtree_version(str(binary))
    assert compatible is False
    assert "Unsupported" in message


def test_tree_validation_rejects_unknown_and_missing_taxa(tmp_path: Path) -> None:
    alignment = tmp_path / "locus.fa"
    alignment.write_text(">a\nAAAA\n>b\nAAAA\n>c\nAAAA\n", encoding="utf-8")
    tree = tmp_path / "tree.nwk"
    tree.write_text("(a,b,x);\n", encoding="utf-8")
    errors = validate_tree(tree, alignment)
    assert any("absent from alignment" in error for error in errors)
    assert any("missing alignment taxa" in error for error in errors)


def test_concordance_normalization_rejects_mismatched_branch_ids(tmp_path: Path) -> None:
    gcf = tmp_path / "gcf.tsv"
    scf = tmp_path / "scf.tsv"
    gcf.write_text("ID\tgCF\n1\t75\n", encoding="utf-8")
    scf.write_text("ID\tsCF\n2\t70\n", encoding="utf-8")
    task = TaskSpec(
        task_id="normalize",
        kind="normalize_concordance",
        argv=[],
        cwd=str(tmp_path),
        inputs=[str(gcf), str(scf)],
        expected_outputs=[str(tmp_path / "summary.tsv")],
    )
    code, message = _normalize_concordance(task)
    assert code == 5
    assert "same branch IDs" in message
