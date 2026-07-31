from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class CuratedAccessionsSummary:
    source_path: str
    n_records: int
    n_unique_taxa: int
    columns: list[str]
    outgroup: str | None


_ACCESSION_ALIASES = {
    "accession",
    "assembly_accession",
    "genbank_accession",
    "ena_accession",
    "sra_accession",
}

_TAXON_ALIASES = {
    "taxon",
    "species",
    "organism",
}


def _find_first_column(df: pd.DataFrame, candidates: set[str]) -> str | None:
    lowered = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c in lowered:
            return lowered[c]
    return None


def load_curated_accessions_table(path: Path) -> pd.DataFrame:
    """Load and validate a curated-accessions table.

    FAIR PhyloFlow schema requirements:
    - at least an accession identifier column (any of _ACCESSION_ALIASES)
    - at least a taxon/organism label column (any of _TAXON_ALIASES)

    Additional columns are preserved and carried through for provenance.
    """

    if not path.exists():
        raise FileNotFoundError(str(path))

    df = pd.read_csv(path, sep=None, engine="python")
    if df.empty:
        raise ValueError("Accessions table is empty")

    accession_col = _find_first_column(df, _ACCESSION_ALIASES)
    taxon_col = _find_first_column(df, _TAXON_ALIASES)

    missing: list[str] = []
    if accession_col is None:
        missing.append("accession (e.g., 'accession' or 'assembly_accession')")
    if taxon_col is None:
        missing.append("taxon (e.g., 'taxon' or 'species')")
    if missing:
        raise ValueError(f"Accessions table missing required columns: {', '.join(missing)}")

    out = df.copy()
    if accession_col != "accession":
        out = out.rename(columns={accession_col: "accession"})
    if taxon_col != "taxon":
        out = out.rename(columns={taxon_col: "taxon"})

    out = out.dropna(subset=["accession", "taxon"])
    out["accession"] = out["accession"].astype(str).str.strip()
    out["taxon"] = out["taxon"].astype(str).str.strip()

    out = out[
        (out["accession"] != "")
        & (out["taxon"] != "")
        & (out["accession"].str.lower() != "nan")
        & (out["taxon"].str.lower() != "nan")
    ]
    if out.empty:
        raise ValueError("Accessions table has no valid rows after stripping/cleaning")

    return out


def summarize_accessions(df: pd.DataFrame, *, source_path: Path, outgroup: str | None) -> CuratedAccessionsSummary:
    return CuratedAccessionsSummary(
        source_path=str(source_path),
        n_records=int(len(df)),
        n_unique_taxa=int(df["taxon"].nunique()),
        columns=[str(c) for c in df.columns],
        outgroup=outgroup,
    )


def write_accessions_normalized_tsv(df: pd.DataFrame, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, sep="\t", index=False)
    return out_path


def write_accessions_registry_json(summary: CuratedAccessionsSummary, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary.__dict__, indent=2), encoding="utf-8")
    return out_path
