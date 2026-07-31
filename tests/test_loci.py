from pathlib import Path

import pandas as pd

from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.loci import classify_loci_for_selection, compute_locus_metrics


def test_classify_loci_records_exclusion_reasons() -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    metrics = pd.DataFrame(
        [
            {"locus_id": "good", "file": "good.fa", "n_taxa": 3, "alignment_length": 100, "mean_missing_fraction": 0.1},
            {
                "locus_id": "missing",
                "file": "missing.fa",
                "n_taxa": 2,
                "alignment_length": 100,
                "mean_missing_fraction": 0.1,
            },
            {"locus_id": "short", "file": "short.fa", "n_taxa": 3, "alignment_length": 0, "mean_missing_fraction": 0.1},
            {
                "locus_id": "gappy",
                "file": "gappy.fa",
                "n_taxa": 3,
                "alignment_length": 100,
                "mean_missing_fraction": 0.9,
            },
        ]
    )

    classified = classify_loci_for_selection(metrics, cfg)

    assert classified.loc[classified["locus_id"] == "good", "selected"].item() is True
    assert "n_taxa<3" in classified.loc[classified["locus_id"] == "missing", "exclusion_reasons"].item()
    assert "alignment_length<1" in classified.loc[classified["locus_id"] == "short", "exclusion_reasons"].item()
    assert "mean_missing_fraction>0.5" in classified.loc[classified["locus_id"] == "gappy", "exclusion_reasons"].item()


def test_classify_loci_excludes_missing_outgroup() -> None:
    cfg = WorkflowConfig.load(Path("examples/penicillium_camemberti_case/project.yaml"))
    metrics = compute_locus_metrics(cfg.input.alignments_dir)

    classified = classify_loci_for_selection(metrics, cfg)
    reasons = classified.loc[
        classified["locus_id"] == "control_locus_missing_outgroup",
        "exclusion_reasons",
    ].item()

    assert "missing_outgroup:Penicillium_fuscoglaucum" in reasons


def test_invalid_alignment_is_explicitly_excluded(tmp_path: Path) -> None:
    alignments = tmp_path / "alignments"
    alignments.mkdir()
    (alignments / "unequal.fa").write_text(">a\nAAAA\n>b\nAAA\n>c\nAAAA\n", encoding="utf-8")
    metrics = compute_locus_metrics(alignments)
    assert bool(metrics.loc[0, "valid"]) is False
    assert metrics.loc[0, "validation_errors"] == "unequal_sequence_lengths"

    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    classified = classify_loci_for_selection(metrics, cfg)
    assert bool(classified.loc[0, "selected"]) is False
    assert "invalid_alignment:unequal_sequence_lengths" in classified.loc[0, "exclusion_reasons"]


def test_invalid_locus_does_not_raise_default_taxon_threshold(tmp_path: Path) -> None:
    (tmp_path / "valid.fa").write_text(">a\nAAAA\n>b\nAAAA\n>c\nAAAA\n", encoding="utf-8")
    (tmp_path / "invalid.fa").write_text(
        ">a\nAAAA\n>b\nAAA\n>c\nAAAA\n>d\nAAAA\n>e\nAAAA\n",
        encoding="utf-8",
    )
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    cfg.input.alignments_dir = tmp_path
    cfg.input.outgroup = None
    selected = classify_loci_for_selection(compute_locus_metrics(tmp_path), cfg).set_index("locus_id")
    assert bool(selected.loc["valid", "selected"]) is True
    assert bool(selected.loc["invalid", "selected"]) is False
