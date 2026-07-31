from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from fair_phyloflow.concordance import interpret_iqtree_concordance
from fair_phyloflow.iqtree_results import summarize_iqtree_run
from fair_phyloflow.packaging import (
    package_fair_outputs,
    verify_fair_package,
    write_checksum_manifest,
    write_ro_crate_metadata,
)
from fair_phyloflow.reporting import write_html_report, write_markdown_report


def test_iqtree_and_concordance_parsers(tmp_path: Path) -> None:
    (tmp_path / "analysis.iqtree").write_text(
        "Best-fit model: GTR+F+G4\nLog-likelihood of the tree: -123.45\nNumber of bootstrap replicates: 1000\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.treefile").write_text("(a,b,c);\n", encoding="utf-8")
    (tmp_path / "analysis.cf.stat").write_text(
        "ID\tgCF\tsCF\tUFBoot\n1\t20\t70\t99\n2\t80\t75\t98\n",
        encoding="utf-8",
    )

    summary = summarize_iqtree_run(tmp_path, "analysis")
    assert summary.best_model == "GTR+F+G4"
    assert summary.log_likelihood == -123.45
    assert summary.ultrafast_bootstrap_reps == 1000
    assert summary.concordance_files == ["analysis.cf.stat"]

    flags = tmp_path / "flags.tsv"
    interpreted = interpret_iqtree_concordance(outdir=tmp_path, prefix="analysis", out_flags_path=flags)
    assert interpreted.status == "computed"
    assert interpreted.n_branches == 2
    assert interpreted.gcf_median == 50.0
    assert "high_support_low_concordance" in flags.read_text(encoding="utf-8")


def test_report_and_fair_package_are_complete(tmp_path: Path) -> None:
    report_dir = tmp_path / "source"
    report_dir.mkdir()
    markdown = write_markdown_report(
        report_dir / "workflow.md",
        project_name="Test project",
        readiness={"status": "ready", "issues": [], "warnings": []},
        resources=None,
        route={"route": "gene_tree", "rationale": ["test"], "warnings": []},
        locus_metrics=pd.DataFrame(
            [
                {
                    "locus_id": "a",
                    "alignment_length": 10,
                    "n_taxa": 3,
                    "mean_missing_fraction": 0.0,
                    "selected": True,
                }
            ]
        ),
        inference={"iqtree_detected": True, "concordance_status": "computed", "warnings": []},
        commands_script=None,
        provenance_path=None,
    )
    html = write_html_report(
        markdown,
        report_dir / "workflow.html",
        templates_dir=Path("src/fair_phyloflow/templates"),
        context={"project_name": "Test project", "generated_at": "now"},
    )
    provenance = report_dir / "provenance.json"
    provenance.write_text('{"version": 1}\n', encoding="utf-8")
    snapshot = report_dir / "project.snapshot.json"
    snapshot.write_text('{"project": {"name": "Test project"}}\n', encoding="utf-8")
    runs = tmp_path / "results" / "08_runs"
    run = runs / "abc123"
    run.mkdir(parents=True)
    (runs / "latest-run.json").write_text(
        json.dumps({"run_id": "abc123", "run_dir": str(run)}),
        encoding="utf-8",
    )
    (run / "run-plan.json").write_text(
        json.dumps(
            {
                "run_dir": str(run),
                "config_path": str(tmp_path / "private" / "project.yaml"),
                "tasks": [{"inputs": [str(run / "inputs" / "locus.fa")]}],
                "fingerprint": "preserved",
            }
        ),
        encoding="utf-8",
    )
    stale_package = tmp_path / "results" / "07_fair_package"
    stale_package.mkdir(parents=True)
    (stale_package / "stale.txt").write_text("must not survive\n", encoding="utf-8")

    package = package_fair_outputs(
        outdir=tmp_path / "results",
        report_md=markdown,
        report_html=html,
        provenance_json=provenance,
        commands_script=None,
        extra_paths=[runs, snapshot],
    )
    manifest = package / "manifest-sha256.tsv"
    crate = package / "ro-crate-metadata.json"
    assert "report.md" in manifest.read_text(encoding="utf-8")
    metadata = json.loads(crate.read_text(encoding="utf-8"))
    assert metadata["@graph"][1]["@type"] == "Dataset"
    assert "<h1>" in (package / "report.html").read_text(encoding="utf-8")
    assert not (package / "stale.txt").exists()
    portable_plan = (package / "08_runs" / "abc123" / "run-plan.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in portable_plan
    assert "${RUN_DIR}/inputs/locus.fa" in portable_plan
    assert "project.yaml" in portable_plan
    assert verify_fair_package(package) == []

    (package / "report.md").write_text("tampered\n", encoding="utf-8")
    errors = verify_fair_package(package)
    assert any("mismatch for report.md" in error for error in errors)


def test_package_verification_requires_core_evidence_and_complete_crate(tmp_path: Path) -> None:
    package = tmp_path / "package"
    package.mkdir()
    for name in ("project.snapshot.json", "provenance.json", "report.html", "report.md"):
        (package / name).write_text("{}\n", encoding="utf-8")
    write_checksum_manifest(package)
    write_ro_crate_metadata(package)
    assert verify_fair_package(package) == []

    (package / "project.snapshot.json").unlink()
    metadata = json.loads((package / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    metadata["@graph"] = [
        entity
        for entity in metadata["@graph"]
        if not (entity.get("@type") == "File" and entity.get("@id") == "report.md")
    ]
    (package / "ro-crate-metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    errors = verify_fair_package(package)
    assert "Missing required package file: project.snapshot.json" in errors
    assert "File is absent from RO-Crate metadata: report.md" in errors
