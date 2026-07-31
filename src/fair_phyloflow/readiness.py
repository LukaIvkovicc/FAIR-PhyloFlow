from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import InputMode, WorkflowConfig
from .loci import classify_loci_for_selection, compute_locus_metrics
from .resources import load_curated_accessions_table


@dataclass(frozen=True)
class ReadinessResult:
    status: str  # ready | caution | not_ready
    issues: list[str]
    warnings: list[str]


def assess_readiness(cfg: WorkflowConfig) -> ReadinessResult:
    issues: list[str] = []
    warnings: list[str] = []
    taxa_df: pd.DataFrame | None = None
    accessions_df: pd.DataFrame | None = None

    if cfg.input.outgroup is None:
        warnings.append("No outgroup specified; rooting/interpretation may be ambiguous.")

    if cfg.input.taxa_table is not None:
        if not cfg.input.taxa_table.exists():
            issues.append(f"Taxa table not found: {cfg.input.taxa_table}")
        else:
            try:
                taxa_df = pd.read_csv(cfg.input.taxa_table, sep=None, engine="python")
                if taxa_df.shape[0] < 3:
                    warnings.append("Taxa table has <3 rows; check taxon sampling.")
                if "taxon" not in {str(c).lower() for c in taxa_df.columns}:
                    warnings.append("Taxa table does not include a taxon column; cross-checks are limited.")
            except (OSError, ValueError, pd.errors.ParserError) as e:
                warnings.append(f"Could not parse taxa table: {e}")

    if cfg.input.mode == InputMode.locus_alignments:
        if cfg.input.alignments_dir is None or not cfg.input.alignments_dir.exists():
            issues.append("Alignments directory missing.")
        else:
            fasta_like = list(cfg.input.alignments_dir.glob("*.fa")) + list(cfg.input.alignments_dir.glob("*.fasta"))
            if len(fasta_like) == 0:
                warnings.append("No .fa/.fasta files detected in alignments dir (MVP expects FASTA).")
            else:
                metrics = compute_locus_metrics(cfg.input.alignments_dir)
                invalid = metrics[~metrics["valid"]] if not metrics.empty else metrics
                if len(invalid) == len(metrics):
                    issues.append("No valid aligned FASTA files detected.")
                elif not invalid.empty:
                    warnings.append(f"{len(invalid)} alignment file(s) are invalid and will be excluded.")
                selected = classify_loci_for_selection(metrics, cfg)
                if not selected.empty and not bool(selected["selected"].any()):
                    issues.append("No alignment passes the configured locus-selection requirements.")

    if cfg.input.mode == InputMode.gene_trees:
        if cfg.input.gene_trees_dir is None or not cfg.input.gene_trees_dir.exists():
            issues.append("Gene trees directory missing.")

    if cfg.input.mode == InputMode.curated_accessions and cfg.input.accessions_table is None:
        issues.append("Accessions table missing.")

    if cfg.input.accessions_table is not None:
        if not cfg.input.accessions_table.exists():
            issues.append("Accessions table missing.")
        else:
            try:
                accessions_df = load_curated_accessions_table(cfg.input.accessions_table)
            except (OSError, ValueError) as e:
                issues.append(f"Accessions table invalid: {e}")

    if cfg.input.outgroup is not None and taxa_df is not None and "taxon" in {str(c).lower() for c in taxa_df.columns}:
        taxon_col = next(c for c in taxa_df.columns if str(c).lower() == "taxon")
        taxa = {str(t).strip() for t in taxa_df[taxon_col].dropna()}
        if cfg.input.outgroup not in taxa:
            warnings.append(f"Declared outgroup not found in taxa table: {cfg.input.outgroup}")

    if cfg.input.outgroup is not None and accessions_df is not None:
        accession_taxa = {str(t).strip() for t in accessions_df["taxon"].dropna()}
        if cfg.input.outgroup not in accession_taxa:
            warnings.append(f"Declared outgroup not found in accessions table: {cfg.input.outgroup}")

    if taxa_df is not None and accessions_df is not None and "taxon" in {str(c).lower() for c in taxa_df.columns}:
        taxon_col = next(c for c in taxa_df.columns if str(c).lower() == "taxon")
        taxa = {str(t).strip() for t in taxa_df[taxon_col].dropna()}
        included = accessions_df
        if "included" in included.columns:
            included = included[included["included"].astype(str).str.lower().isin({"true", "1", "yes", "y"})]
        accession_taxa = {str(t).strip() for t in included["taxon"].dropna()}
        missing_from_taxa = sorted(accession_taxa - taxa)
        missing_from_accessions = sorted(taxa - accession_taxa)
        if missing_from_taxa:
            warnings.append(f"Included accession taxa not found in taxa table: {', '.join(missing_from_taxa)}")
        if missing_from_accessions:
            warnings.append(
                f"Taxa table entries not represented by included accessions: {', '.join(missing_from_accessions)}"
            )

    if issues:
        return ReadinessResult(status="not_ready", issues=issues, warnings=warnings)
    if warnings:
        return ReadinessResult(status="caution", issues=[], warnings=warnings)
    return ReadinessResult(status="ready", issues=[], warnings=[])
