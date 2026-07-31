from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class ConcordanceInterpretation:
    status: str  # not_requested | not_computed | computed | partial
    table_path: str | None
    n_branches: int | None
    gcf_median: float | None
    scf_median: float | None
    flags_path: str | None
    warnings: list[str]


def _find_cf_table(outdir: Path, prefix: str) -> Path | None:
    # IQ-TREE commonly writes concordance summaries as *.cf.stat
    candidates = [outdir / f"{prefix}.cf.stat"]
    # fallback: any matching cf.stat
    candidates += sorted(outdir.glob(f"{prefix}*.cf.stat"))
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _get_col(df: pd.DataFrame, *names: str) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for n in names:
        key = n.lower()
        if key in lower:
            return lower[key]
    return None


def interpret_iqtree_concordance(
    *,
    outdir: Path,
    prefix: str,
    out_flags_path: Path | None = None,
    gcf_high: float = 50.0,
    gcf_low: float = 25.0,
    scf_high: float = 50.0,
    scf_low: float = 25.0,
) -> ConcordanceInterpretation:
    """Best-effort concordance interpretation from IQ-TREE concordance outputs.

    - If a concordance table exists, writes a branch-level flag table (optional).
    - If support columns are present (e.g., Bootstrap/UFBoot), uses them; otherwise flags are concordance-only.
    """

    cf_path = _find_cf_table(outdir, prefix)
    if cf_path is None:
        return ConcordanceInterpretation(
            status="not_computed",
            table_path=None,
            n_branches=None,
            gcf_median=None,
            scf_median=None,
            flags_path=None,
            warnings=["No IQ-TREE concordance table (*.cf.stat) detected."],
        )

    try:
        df = pd.read_csv(cf_path, sep=None, engine="python")
    except Exception as e:  # pragma: no cover
        return ConcordanceInterpretation(
            status="partial",
            table_path=str(cf_path),
            n_branches=None,
            gcf_median=None,
            scf_median=None,
            flags_path=None,
            warnings=[f"Could not parse concordance table: {e}"],
        )

    df = _normalize_cols(df)
    gcf_col = _get_col(df, "gCF", "gcf")
    scf_col = _get_col(df, "sCF", "scf")
    boot_col = _get_col(df, "Bootstrap", "UFBoot", "UFboot", "ufboot")

    warnings: list[str] = []
    if gcf_col is None and scf_col is None:
        warnings.append("Concordance table parsed but gCF/sCF columns were not found; file format may differ.")

    out_df = pd.DataFrame()
    out_df["branch"] = (
        df[_get_col(df, "Branch", "branch", "ID", "id")].astype(str)
        if _get_col(df, "Branch", "branch", "ID", "id")
        else df.index.astype(str)
    )

    if boot_col is not None:
        out_df["support"] = pd.to_numeric(df[boot_col], errors="coerce")

    if gcf_col is not None:
        out_df["gCF"] = pd.to_numeric(df[gcf_col], errors="coerce")
    if scf_col is not None:
        out_df["sCF"] = pd.to_numeric(df[scf_col], errors="coerce")

    def _flag_row(row: pd.Series) -> str:
        g = row.get("gCF")
        s = row.get("sCF")
        sup = row.get("support")

        # Prefer combined support+concordance if available
        if sup is not None and pd.notna(sup):
            sup_high = float(sup) >= 95.0
        else:
            sup_high = None

        g_high = g is not None and pd.notna(g) and float(g) >= gcf_high
        g_lowv = g is not None and pd.notna(g) and float(g) <= gcf_low
        s_high = s is not None and pd.notna(s) and float(s) >= scf_high
        s_lowv = s is not None and pd.notna(s) and float(s) <= scf_low

        if sup_high is True and (g_lowv or s_lowv):
            return "high_support_low_concordance"
        if sup_high is True and (g_high or s_high):
            return "high_support_high_concordance"
        if (g_lowv or s_lowv) and sup_high is None:
            return "low_concordance"
        if (g_high or s_high) and sup_high is None:
            return "high_concordance"
        return "unflagged"

    out_df["flag"] = out_df.apply(_flag_row, axis=1)

    flags_path: str | None = None
    if out_flags_path is not None:
        out_flags_path.parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(out_flags_path, sep="\t", index=False)
        flags_path = str(out_flags_path)

    gcf_median = float(out_df["gCF"].median()) if "gCF" in out_df.columns and out_df["gCF"].notna().any() else None
    scf_median = float(out_df["sCF"].median()) if "sCF" in out_df.columns and out_df["sCF"].notna().any() else None

    return ConcordanceInterpretation(
        status="computed",
        table_path=str(cf_path),
        n_branches=int(len(out_df)),
        gcf_median=gcf_median,
        scf_median=scf_median,
        flags_path=flags_path,
        warnings=warnings,
    )
