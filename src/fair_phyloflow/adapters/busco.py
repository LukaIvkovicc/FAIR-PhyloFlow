from __future__ import annotations

from pathlib import Path

from fair_phyloflow.adapters.base import AdapterCapability, PlannedCommand, SupportLevel, ToolAdapter, ToolVersion
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.execution import ToolStatus, safe_run_version, which
from fair_phyloflow.routes import RouteId


class BuscoAdapter(ToolAdapter):
    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            tool_id="busco",
            label="BUSCO (completeness / marker suitability)",
            # BUSCO is conceptually Stage 3, but we surface it in command planning as an optional pre-step.
            routes={RouteId.concatenation, RouteId.gene_tree, RouteId.species_tree, RouteId.conflict},
            support=SupportLevel.guided,
        )

    def detect(self, cfg: WorkflowConfig) -> ToolStatus:
        return which(cfg.execution.busco_bin)

    def version(self, cfg: WorkflowConfig) -> ToolVersion:
        st = self.detect(cfg)
        ver: str | None = None
        if st.available:
            ver = safe_run_version([cfg.execution.busco_bin, "--version"])
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
        _ = (route, loci_dir, concat_alignment, loci_count)
        cmd = (
            "# BUSCO completeness / marker suitability (Stage 3).\n"
            "# Requires assemblies/proteomes (not alignments). Provide BUSCO lineage explicitly.\n"
            "# Example (placeholder):\n"
            "# export BUSCO_LINEAGE=fungi_odb10\n"
            f"# {cfg.execution.busco_bin} -i <assembly_or_proteins.fasta> -l $BUSCO_LINEAGE "
            f"-m genome -o busco_out -c {cfg.execution.busco_cores}"
        )
        return [PlannedCommand(label="BUSCO completeness (placeholder)", command=cmd, cwd=workdir)]
