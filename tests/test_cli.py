from __future__ import annotations

import json
import os
import socket
from pathlib import Path

import yaml
from typer.testing import CliRunner

from fair_phyloflow import PRODUCT_NAME, __version__
from fair_phyloflow.cli import app

runner = CliRunner()


def test_version_option() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"{PRODUCT_NAME} {__version__}" in result.stdout


def test_configuration_errors_follow_exit_contract(tmp_path: Path) -> None:
    missing = runner.invoke(app, ["check", str(tmp_path / "missing.yaml")])
    assert missing.exit_code == 2
    assert "Configuration error:" in missing.stdout

    malformed = tmp_path / "malformed.yaml"
    malformed.write_text("project: [\n", encoding="utf-8")
    invalid = runner.invoke(app, ["check", str(malformed)])
    assert invalid.exit_code == 2
    assert "Configuration error:" in invalid.stdout


def _config(tmp_path: Path) -> Path:
    config = {
        "project": {"name": "cli_test", "outdir": str(tmp_path / "results")},
        "question": {"type": "species_delimitation", "needs_concordance": True},
        "input": {
            "mode": "locus_alignments",
            "alignments_dir": str(Path("examples/demo_project/alignments").resolve()),
            "taxa_table": str(Path("examples/demo_project/taxa.tsv").resolve()),
            "outgroup": "Penicillium_outgroup",
        },
        "analysis": {"threads": 1, "bootstrap_replicates": 10, "concordance_quartets": 10},
        "execution": {"iqtree_bin": "definitely-missing-iqtree"},
    }
    path = tmp_path / "project.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_execute_plan_only_and_missing_tool_exit_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    planned = runner.invoke(app, ["execute", str(config), "--plan-only"])
    assert planned.exit_code == 0
    assert "Plan fingerprint" in planned.stdout
    latest_path = tmp_path / "results" / "08_runs" / "latest-run.json"
    latest = yaml.safe_load(latest_path.read_text(encoding="utf-8"))
    run_dir = latest_path.parent / latest["run_id"]
    assert (run_dir / "run-plan.json").exists()
    assert len(list((run_dir / "inputs" / "loci").glob("*.fa"))) == 2
    manifest = (run_dir / "inputs" / "input-manifest.tsv").read_text(encoding="utf-8")
    assert "source_path" in manifest
    assert str(tmp_path) not in manifest

    executed = runner.invoke(app, ["execute", str(config)])
    assert executed.exit_code == 3
    assert "IQ-TREE executable not found" in executed.stdout


def test_execute_lock_uses_operational_block_exit_contract(tmp_path: Path) -> None:
    config = _config(tmp_path)
    planned = runner.invoke(app, ["execute", str(config), "--plan-only"])
    assert planned.exit_code == 0
    latest_path = tmp_path / "results" / "08_runs" / "latest-run.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    lock_path = latest_path.parent / latest["run_id"] / ".run.lock"
    lock_path.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
                "created_at_utc": "test",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    blocked = runner.invoke(app, ["execute", str(config)])
    assert blocked.exit_code == 4
    assert "Run is already locked" in blocked.stdout
    assert "Expose a compatible IQ-TREE" not in blocked.stdout


def test_check_command_reports_readiness(tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(_config(tmp_path))])
    assert result.exit_code == 0
    assert "Readiness:" in result.stdout


def test_nonexecuting_cli_workflow_generates_report_and_package(tmp_path: Path) -> None:
    config = _config(tmp_path)
    for command in ("status", "plan"):
        result = runner.invoke(app, [command, str(config)])
        assert result.exit_code == 0, result.stdout

    generated = runner.invoke(app, ["run", str(config), "--no-execute"])
    assert generated.exit_code == 0
    assert "Wrote commands" in generated.stdout

    reported = runner.invoke(app, ["report", str(config)])
    assert reported.exit_code == 0
    packaged = runner.invoke(app, ["package", str(config)])
    assert packaged.exit_code == 0

    package = tmp_path / "results" / "07_fair_package"
    assert (package / "report.html").exists()
    assert (package / "manifest-sha256.tsv").exists()
    assert (package / "ro-crate-metadata.json").exists()
    snapshot = (package / "project.snapshot.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in snapshot
    verified = runner.invoke(app, ["verify-package", str(package)])
    assert verified.exit_code == 0
    assert "Package verified" in verified.stdout


def test_report_prefers_authoritative_structured_outputs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert runner.invoke(app, ["execute", str(config), "--plan-only"]).exit_code == 0
    latest_path = tmp_path / "results" / "08_runs" / "latest-run.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    run_dir = latest_path.parent / latest["run_id"]
    reference = run_dir / "outputs" / "reference"
    concordance = run_dir / "outputs" / "concordance"
    reference.mkdir(parents=True)
    concordance.mkdir(parents=True)
    (reference / "concatenated.iqtree").write_text(
        "Best-fit model: GTR+F+G4\nLog-likelihood of the tree: -42.5\n",
        encoding="utf-8",
    )
    (reference / "concatenated.treefile").write_text("(a,b,c);\n", encoding="utf-8")
    (concordance / "branch-summary.tsv").write_text("ID\tgCF\tsCF\n1\t70\t60\n", encoding="utf-8")
    (run_dir / "run-state.json").write_text(
        json.dumps({"status": "complete", "tasks": {"reference_tree": {"status": "verified"}}}),
        encoding="utf-8",
    )

    reported = runner.invoke(app, ["report", str(config)])
    assert reported.exit_code == 0, reported.stdout
    report = (tmp_path / "results" / "07_fair_package" / "workflow_report.md").read_text(encoding="utf-8")
    assert "IQ-TREE outputs detected: **True**" in report
    assert "best_model: GTR+F+G4" in report
    assert "concordance_status: computed" in report
    assert "gcf_median: 70.0" in report


def test_run_propagates_tool_failure_and_omits_zero_bootstrap(tmp_path: Path) -> None:
    executable = tmp_path / "failing-iqtree"
    captured = tmp_path / "arguments.txt"
    executable.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' "$@" > "' + str(captured) + '"\nexit 9\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    config = _config(tmp_path)
    value = yaml.safe_load(config.read_text(encoding="utf-8"))
    value["execution"]["iqtree_bin"] = str(executable)
    value["analysis"]["bootstrap_replicates"] = 0
    config.write_text(yaml.safe_dump(value), encoding="utf-8")

    result = runner.invoke(app, ["run", str(config)])
    assert result.exit_code == 5
    arguments = captured.read_text(encoding="utf-8").splitlines()
    assert "-B" not in arguments


def test_report_rejects_unsafe_latest_run_reference(tmp_path: Path) -> None:
    config = _config(tmp_path)
    results = tmp_path / "results"
    runs = results / "08_runs"
    runs.mkdir(parents=True)
    (runs / "latest-run.json").write_text(
        json.dumps({"run_id": "../outside", "run_dir": str(tmp_path / "outside")}),
        encoding="utf-8",
    )
    result = runner.invoke(app, ["report", str(config)])
    assert result.exit_code == 0
    report = (results / "07_fair_package" / "workflow_report.md").read_text(encoding="utf-8")
    assert "run_state:" not in report
