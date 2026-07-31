from __future__ import annotations

import shlex
from pathlib import Path

from fair_phyloflow.adapters.base import AdapterCapability, PlannedCommand, SupportLevel, ToolAdapter, ToolVersion
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.execution import ToolStatus, safe_run_version, which
from fair_phyloflow.routes import RouteId


class RaxmlNGAdapter(ToolAdapter):
    def capability(self) -> AdapterCapability:
        return AdapterCapability(
            tool_id="raxml-ng",
            label="RAxML-NG",
            routes={RouteId.concatenation, RouteId.gene_tree},
            support=SupportLevel.command,
        )

    def detect(self, cfg: WorkflowConfig) -> ToolStatus:
        return which(cfg.execution.raxmlng_bin)

    def version(self, cfg: WorkflowConfig) -> ToolVersion:
        st = self.detect(cfg)
        ver: str | None = None
        if st.available:
            ver = safe_run_version([cfg.execution.raxmlng_bin, "--version"])
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
        _ = loci_count
        cmds: list[PlannedCommand] = []
        threads = cfg.analysis.threads
        replicates = cfg.analysis.bootstrap_replicates
        mode = "--all" if replicates > 0 else "--search"
        bootstrap_args = ["--bs-trees", str(replicates)] if replicates > 0 else []

        if route in {RouteId.concatenation, RouteId.gene_tree} and concat_alignment is not None:
            argv = [
                cfg.execution.raxmlng_bin,
                mode,
                "--msa",
                str(concat_alignment),
                "--model",
                "GTR+G",
                *bootstrap_args,
                "--threads",
                str(threads),
                "--prefix",
                str(workdir / "raxml_concatenated"),
            ]
            cmd = shlex.join(argv)
            cmds.append(PlannedCommand(label="Concatenated ML tree (RAxML-NG)", command=cmd, cwd=workdir))

        if route == RouteId.gene_tree and loci_dir is not None:
            bootstrap_template = f" --bs-trees {replicates}" if replicates > 0 else ""
            cmd = (
                "# Per-locus RAxML-NG is typically run via job arrays/HPC wrappers.\n"
                f"# Input directory: {loci_dir.as_posix()}\n"
                "# Example per-locus command template:\n"
                f"# {cfg.execution.raxmlng_bin} {mode} --msa <locus.fasta> --model GTR+G{bootstrap_template} "
                f"--threads {threads} --prefix <out>"
            )
            cmds.append(PlannedCommand(label="Per-locus ML gene trees (RAxML-NG template)", command=cmd, cwd=workdir))

        return cmds
