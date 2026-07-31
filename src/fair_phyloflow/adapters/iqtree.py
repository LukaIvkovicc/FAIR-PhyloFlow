from __future__ import annotations

import shlex
from pathlib import Path

from fair_phyloflow.adapters.base import (
    AdapterCapability,
    PlannedCommand,
    SupportLevel,
    ToolAdapter,
    ToolVersion,
)
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.execution import ToolStatus, safe_run_version, which
from fair_phyloflow.routes import RouteId


class IQTreeAdapter(ToolAdapter):
    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            tool_id="iqtree2",
            label="IQ-TREE 2",
            routes={RouteId.concatenation, RouteId.gene_tree},
            support=SupportLevel.parsed,
        )

    def detect(self, cfg: WorkflowConfig) -> ToolStatus:
        # Respect user override for binary name
        return which(cfg.execution.iqtree_bin)

    def version(self, cfg: WorkflowConfig) -> ToolVersion:
        st = self.detect(cfg)
        ver: str | None = None
        if st.available:
            ver = safe_run_version([cfg.execution.iqtree_bin, "-version"])
        return ToolVersion(
            tool_id=self.capability().tool_id, available=st.available, path=st.resolved_path, version=ver
        )

    def _concat_cmd(self, cfg: WorkflowConfig, concatenated_alignment: Path, outdir: Path) -> str:
        argv = [cfg.execution.iqtree_bin, "-s", str(concatenated_alignment), "-m", "MFP"]
        if cfg.analysis.bootstrap_replicates > 0:
            argv.extend(["-B", str(cfg.analysis.bootstrap_replicates)])
        argv.extend(
            [
                "-T",
                str(cfg.analysis.threads),
                "-seed",
                str(cfg.analysis.random_seed),
                "--prefix",
                str(outdir / "concatenated"),
            ]
        )
        return shlex.join(argv)

    def _per_locus_cmd(self, cfg: WorkflowConfig, loci_dir: Path, outdir: Path) -> str:
        argv = [cfg.execution.iqtree_bin, "-S", str(loci_dir), "-m", "MFP"]
        if cfg.analysis.bootstrap_replicates > 0:
            argv.extend(["-B", str(cfg.analysis.bootstrap_replicates)])
        argv.extend(
            [
                "-T",
                str(cfg.analysis.threads),
                "-seed",
                str(cfg.analysis.random_seed),
                "--prefix",
                str(outdir / "gene"),
            ]
        )
        return shlex.join(argv)

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
        _ = loci_count
        cmds: list[PlannedCommand] = []
        if route in {RouteId.concatenation, RouteId.gene_tree} and concat_alignment is not None:
            cmds.append(
                PlannedCommand(
                    label="Concatenated ML tree (IQ-TREE 2)",
                    command=self._concat_cmd(cfg, concat_alignment, workdir),
                    cwd=workdir,
                )
            )
        if route == RouteId.gene_tree and loci_dir is not None:
            cmds.append(
                PlannedCommand(
                    label="Per-locus gene trees (IQ-TREE 2)",
                    command=self._per_locus_cmd(cfg, loci_dir, workdir),
                    cwd=workdir,
                )
            )
        return cmds
