from __future__ import annotations

from pathlib import Path

from fair_phyloflow.adapters.base import AdapterCapability, PlannedCommand, SupportLevel, ToolAdapter, ToolVersion
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.execution import ToolStatus, safe_run_version, which
from fair_phyloflow.routes import RouteId


class AstralAdapter(ToolAdapter):
    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            tool_id="astral",
            label="ASTRAL",
            routes={RouteId.species_tree},
            support=SupportLevel.guided,
        )

    def detect(self, cfg: WorkflowConfig) -> ToolStatus:
        return which(cfg.execution.astral_bin)

    def version(self, cfg: WorkflowConfig) -> ToolVersion:
        st = self.detect(cfg)
        ver: str | None = None
        if st.available:
            ver = safe_run_version([cfg.execution.astral_bin, "-v"])
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
        _ = (cfg, concat_alignment, loci_count)
        if route != RouteId.species_tree:
            return []

        cmd = (
            "# Species-tree inference from gene trees (ASTRAL).\n"
            "# Requires a single file containing gene trees in Newick format (often concatenated).\n"
            "# If you inferred per-locus trees, concatenate them into one file (or point ASTRAL to it).\n"
            f"{cfg.execution.astral_bin} -i <gene_trees.tre> -o {workdir.as_posix()}/species_tree_astral.tre"
        )
        return [PlannedCommand(label="Species tree (ASTRAL)", command=cmd, cwd=workdir)]
