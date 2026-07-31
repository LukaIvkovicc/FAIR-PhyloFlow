from __future__ import annotations

from pathlib import Path

from fair_phyloflow.adapters.base import AdapterCapability, PlannedCommand, SupportLevel, ToolAdapter, ToolVersion
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.execution import ToolStatus, safe_run_version, which
from fair_phyloflow.routes import RouteId


class BuckyAdapter(ToolAdapter):
    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            tool_id="bucky",
            label="BUCKy (Bayesian concordance)",
            routes={RouteId.conflict, RouteId.gene_tree},
            support=SupportLevel.guided,
        )

    def detect(self, cfg: WorkflowConfig) -> ToolStatus:
        return which(cfg.execution.bucky_bin)

    def version(self, cfg: WorkflowConfig) -> ToolVersion:
        st = self.detect(cfg)
        ver: str | None = None
        if st.available:
            ver = safe_run_version([cfg.execution.bucky_bin, "--version"])
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
        _ = (loci_dir, concat_alignment, loci_count)
        if route not in {RouteId.conflict, RouteId.gene_tree}:
            return []

        cmd = (
            "# BUCKy is typically used with posterior gene tree distributions (from Bayesian phylogenetics),\n"
            "# not with single ML trees. This workflow treats it as an advanced, guidance-only option.\n"
            "# If you have per-locus posterior tree samples, see BUCKy documentation for input preparation.\n"
            f"# Example (placeholder):\n# {cfg.execution.bucky_bin} -n 4 -a 1 -o {workdir.as_posix()}/bucky_out <locus1.trees> <locus2.trees> ..."
        )
        return [PlannedCommand(label="Bayesian concordance (BUCKy) guidance", command=cmd, cwd=workdir)]
