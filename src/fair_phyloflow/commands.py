from __future__ import annotations

import os
from pathlib import Path

from .adapters.registry import adapters_for_route
from .config import WorkflowConfig
from .routes import RouteId


def write_commands_script(
    cfg: WorkflowConfig,
    route: RouteId,
    *,
    workdir: Path,
    outputs_dir: Path | None = None,
    loci_dir: Path | None,
    concat_alignment: Path | None,
    loci_count: int | None,
) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    command_outputs_dir = outputs_dir if outputs_dir is not None else workdir
    command_outputs_dir.mkdir(parents=True, exist_ok=True)
    script = workdir / "reproducible_commands.sh"
    lines: list[str] = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        'SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"',
        'cd "$SCRIPT_DIR"',
        "",
    ]
    portable_outputs_dir = Path(os.path.relpath(command_outputs_dir, workdir))
    portable_loci_dir = Path(os.path.relpath(loci_dir, workdir)) if loci_dir is not None else None
    portable_concat = Path(os.path.relpath(concat_alignment, workdir)) if concat_alignment is not None else None

    # Route-aware command planning via adapters
    planned_any = False
    for adapter in adapters_for_route(cfg, route):
        for planned in adapter.plan_commands(
            cfg,
            route=route,
            workdir=portable_outputs_dir,
            loci_dir=portable_loci_dir,
            concat_alignment=portable_concat,
            loci_count=loci_count,
        ):
            planned_any = True
            lines += [f"# {planned.label}", planned.command, ""]

    if cfg.question.needs_concordance or cfg.analysis.require_concordance:
        lines += [
            "# Concordance (cross-cutting interpretive step)",
            "# Requires: a reference tree + a set of gene trees.",
            "# If you inferred per-locus trees, point --gcf at the gene-tree file(s)/directory.",
            "# Example (adjust paths as needed):",
            f"# {cfg.execution.iqtree_bin} -t ../05_trees/concatenated.treefile --gcf <gene_trees> --scf 100",
            "",
        ]

    if not planned_any:
        lines += [
            "# No executable adapter available for this route in the current environment.",
            "# This is expected for guidance-only routes in the MVP.",
            "",
        ]

    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return script
