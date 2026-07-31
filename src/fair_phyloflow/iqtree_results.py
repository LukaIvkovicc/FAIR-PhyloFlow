from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IQTreeRunSummary:
    prefix: str
    iqtree_file: str | None
    treefile: str | None
    contree: str | None
    best_model: str | None
    log_likelihood: float | None
    ultrafast_bootstrap_reps: int | None
    concordance_files: list[str]


_RE_MODEL = re.compile(r"^Best-fit model:\s+(?P<model>.+?)\s*$")
_RE_LOGL = re.compile(r"^Log-likelihood of the tree:\s+(?P<ll>-?\d+(?:\.\d+)?)")
_RE_UFB = re.compile(r"^Number of bootstrap replicates:\s+(?P<n>\d+)")


def _extract_from_iqtree_text(text: str) -> tuple[str | None, float | None, int | None]:
    best_model: str | None = None
    logl: float | None = None
    ufb: int | None = None

    for line in text.splitlines():
        if best_model is None:
            m = _RE_MODEL.match(line.strip())
            if m:
                best_model = m.group("model").strip()
                continue
        if logl is None:
            m = _RE_LOGL.match(line.strip())
            if m:
                try:
                    logl = float(m.group("ll"))
                except ValueError:
                    logl = None
                continue
        if ufb is None:
            m = _RE_UFB.match(line.strip())
            if m:
                try:
                    ufb = int(m.group("n"))
                except ValueError:
                    ufb = None
                continue

    return best_model, logl, ufb


def summarize_iqtree_run(outdir: Path, prefix: str) -> IQTreeRunSummary:
    """Summarize IQ-TREE outputs for a given prefix inside outdir.

    Looks for standard output files:
    - <prefix>.iqtree
    - <prefix>.treefile
    - <prefix>.contree
    - concordance outputs: <prefix>.cf.* or <prefix>.*.cf.*
    """

    iqtree = outdir / f"{prefix}.iqtree"
    treefile = outdir / f"{prefix}.treefile"
    contree = outdir / f"{prefix}.contree"

    best_model: str | None = None
    logl: float | None = None
    ufb: int | None = None

    if iqtree.exists():
        text = iqtree.read_text(encoding="utf-8", errors="replace")
        best_model, logl, ufb = _extract_from_iqtree_text(text)

    concordance_files = sorted({p.name for p in outdir.glob(f"{prefix}*.cf.*")})

    return IQTreeRunSummary(
        prefix=prefix,
        iqtree_file=str(iqtree) if iqtree.exists() else None,
        treefile=str(treefile) if treefile.exists() else None,
        contree=str(contree) if contree.exists() else None,
        best_model=best_model,
        log_likelihood=logl,
        ultrafast_bootstrap_reps=ufb,
        concordance_files=concordance_files,
    )
