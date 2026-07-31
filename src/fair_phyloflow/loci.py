from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from Bio import SeqIO

from .config import WorkflowConfig


def _missing_fraction(seq: str) -> float:
    if not seq:
        return 1.0
    missing = 0
    for ch in seq.upper():
        if ch in {"-", "N", "?"}:
            missing += 1
    return missing / len(seq)


def compute_locus_metrics(alignments_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(list(alignments_dir.glob("*.fa")) + list(alignments_dir.glob("*.fasta"))):
        validation_errors: list[str] = []
        try:
            records = list(SeqIO.parse(str(path), "fasta"))
        except (OSError, ValueError) as exc:
            records = []
            validation_errors.append(f"parse_error:{exc}")
        if not records and not validation_errors:
            validation_errors.append("no_records")
        lengths = {len(str(r.seq)) for r in records}
        if len(lengths) > 1:
            validation_errors.append("unequal_sequence_lengths")
        identifiers = [record.id for record in records]
        if len(identifiers) != len(set(identifiers)):
            validation_errors.append("duplicate_taxon_ids")
        aln_len = max(lengths) if lengths else 0
        mf = sum(_missing_fraction(str(r.seq)) for r in records) / len(records) if records else 1.0
        rows.append(
            {
                "locus_id": path.stem,
                "file": path.name,
                "n_taxa": len(set(identifiers)),
                "alignment_length": int(aln_len),
                "mean_missing_fraction": float(mf),
                "valid": not validation_errors,
                "validation_errors": ";".join(validation_errors),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "locus_id",
            "file",
            "n_taxa",
            "alignment_length",
            "mean_missing_fraction",
            "valid",
            "validation_errors",
        ],
    )


def classify_loci_for_selection(metrics: pd.DataFrame, cfg: WorkflowConfig) -> pd.DataFrame:
    """Add transparent selection decisions without claiming biological optimality."""
    if metrics.empty:
        return metrics.assign(selected=pd.Series(dtype=bool), exclusion_reasons=pd.Series(dtype=str))

    min_taxa = cfg.analysis.min_taxa_per_locus
    if min_taxa is None:
        valid_metrics = metrics[metrics["valid"].astype(bool)] if "valid" in metrics.columns else metrics
        min_taxa = max(3, int(valid_metrics["n_taxa"].max())) if not valid_metrics.empty else 3

    rows: list[dict[str, Any]] = []
    for raw_row in metrics.to_dict(orient="records"):
        row: dict[str, Any] = {str(key): value for key, value in raw_row.items()}
        reasons: list[str] = []
        if not bool(row.get("valid", True)):
            reasons.append(f"invalid_alignment:{row.get('validation_errors', 'unknown')}")
        if int(row["alignment_length"]) < cfg.analysis.min_alignment_length:
            reasons.append(f"alignment_length<{cfg.analysis.min_alignment_length}")
        if float(row["mean_missing_fraction"]) > cfg.analysis.max_mean_missing_fraction:
            reasons.append(f"mean_missing_fraction>{cfg.analysis.max_mean_missing_fraction}")
        if int(row["n_taxa"]) < min_taxa:
            reasons.append(f"n_taxa<{min_taxa}")
        if cfg.input.outgroup is not None and bool(row.get("valid", True)):
            locus_path = Path(str(row["file"]))
            if not locus_path.is_absolute() and cfg.input.alignments_dir is not None:
                locus_path = cfg.input.alignments_dir / locus_path
            records = list(SeqIO.parse(str(locus_path), "fasta")) if locus_path.exists() else []
            if records and cfg.input.outgroup not in {r.id for r in records}:
                reasons.append(f"missing_outgroup:{cfg.input.outgroup}")

        row["selected"] = not reasons
        row["exclusion_reasons"] = ";".join(reasons)
        rows.append(row)

    return pd.DataFrame(rows)
