from __future__ import annotations

import shlex
from pathlib import Path

from fair_phyloflow.adapters.base import AdapterCapability, PlannedCommand, SupportLevel, ToolAdapter, ToolVersion
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.execution import ToolStatus, safe_run_version, which
from fair_phyloflow.routes import RouteId


class ParGenesAdapter(ToolAdapter):
    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            tool_id="pargenes",
            label="ParGenes",
            routes={RouteId.gene_tree},
            support=SupportLevel.command,
        )

    def detect(self, cfg: WorkflowConfig) -> ToolStatus:
        return which(cfg.execution.pargenes_bin)

    def version(self, cfg: WorkflowConfig) -> ToolVersion:
        st = self.detect(cfg)
        ver: str | None = None
        if st.available:
            ver = safe_run_version([cfg.execution.pargenes_bin, "--version"])
        return ToolVersion(
            tool_id=self.capability().tool_id, available=st.available, path=st.resolved_path, version=ver
        )

    def plan_commands(
        self,
        cfg: WorkflowConfig,
        *,
        route: RouteId,
        workdir: Path,
        loci_dir: Path | None,
        concat_alignment: Path | None,
        loci_count: int | None,
    ) -> list[PlannedCommand]:
        _ = concat_alignment
        if route != RouteId.gene_tree or loci_dir is None:
            return []
        if loci_count is not None and loci_count < cfg.analysis.large_locus_threshold:
            return []

        argv = [
            cfg.execution.pargenes_bin,
            "-a",
            str(loci_dir),
            "-o",
            str(workdir / "pargenes_out"),
            "-c",
            str(cfg.execution.pargenes_cores),
            "-d",
            "nt",
            "-m",
        ]
        if cfg.analysis.bootstrap_replicates > 0:
            argv.extend(["-b", str(cfg.analysis.bootstrap_replicates)])
        cmd = "\n".join(
            [
                "# ParGenes scalable per-locus inference (HPC-oriented).",
                "# The current prepared-alignment contract is nucleotide FASTA; ModelTest-NG selects per-locus models.",
                shlex.join(argv),
            ]
        )
        return [PlannedCommand(label="ParGenes scalable per-locus inference", command=cmd, cwd=workdir)]
