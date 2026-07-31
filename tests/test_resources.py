from __future__ import annotations

from pathlib import Path

import pytest

from fair_phyloflow.resources import load_curated_accessions_table


def test_load_curated_accessions_accepts_alias_columns(tmp_path: Path) -> None:
    p = tmp_path / "acc.tsv"
    p.write_text("assembly_accession\tspecies\nGCF_000001\tPenicillium_camemberti\n", encoding="utf-8")
    df = load_curated_accessions_table(p)
    assert set(df.columns) >= {"accession", "taxon"}
    assert df.loc[0, "accession"] == "GCF_000001"


def test_load_curated_accessions_requires_accession_and_taxon(tmp_path: Path) -> None:
    p = tmp_path / "acc.tsv"
    p.write_text("foo\tbar\n1\t2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_curated_accessions_table(p)


def test_accessions_loader_drops_null_identifiers(tmp_path: Path) -> None:
    path = tmp_path / "accessions.tsv"
    path.write_text("accession\ttaxon\nGCF_1\tTaxon_a\n\tTaxon_b\nGCF_3\t\n", encoding="utf-8")
    loaded = load_curated_accessions_table(path)
    assert loaded[["accession", "taxon"]].to_dict(orient="records") == [{"accession": "GCF_1", "taxon": "Taxon_a"}]
