from __future__ import annotations

from pathlib import Path

import pytest

from fair_phyloflow.concatenate import concatenate_alignments


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_concatenate_backfills_taxa_that_appear_later(tmp_path: Path) -> None:
    alignments = tmp_path / "alignments"
    alignments.mkdir()
    _write(alignments / "a.fa", ">taxon_a\nAAAA\n")
    _write(alignments / "b.fa", ">taxon_a\nCC\n>taxon_b\nGG\n")

    out = tmp_path / "concat.fa"
    concatenate_alignments(alignments, out)

    assert ">taxon_a\nAAAACC\n" in out.read_text(encoding="utf-8")
    assert ">taxon_b\n----GG\n" in out.read_text(encoding="utf-8")


def test_concatenate_uses_only_selected_loci(tmp_path: Path) -> None:
    alignments = tmp_path / "alignments"
    alignments.mkdir()
    selected = _write(alignments / "selected.fa", ">taxon_a\nAAAA\n>taxon_b\nCCCC\n")
    _write(alignments / "excluded.fa", ">taxon_a\nGGGG\n>taxon_b\nTTTT\n")

    out = tmp_path / "concat.fa"
    concatenate_alignments(alignments, out, loci_paths=[selected])

    text = out.read_text(encoding="utf-8")
    assert "AAAA" in text
    assert "GGGG" not in text


def test_concatenate_rejects_unequal_lengths(tmp_path: Path) -> None:
    alignments = tmp_path / "alignments"
    alignments.mkdir()
    _write(alignments / "bad.fa", ">taxon_a\nAAAA\n>taxon_b\nCC\n")

    with pytest.raises(ValueError, match="unequal sequence lengths"):
        concatenate_alignments(alignments, tmp_path / "concat.fa")
