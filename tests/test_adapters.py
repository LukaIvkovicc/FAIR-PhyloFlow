from __future__ import annotations

from pathlib import Path

from fair_phyloflow.adapters.base import ToolAdapter
from fair_phyloflow.adapters.registry import adapters_for_route, default_adapters
from fair_phyloflow.commands import write_commands_script
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.routes import RouteId


def _adapter(cfg: WorkflowConfig, tool_id: str) -> ToolAdapter:
    return next(adapter for adapter in default_adapters(cfg) if adapter.capability().tool_id == tool_id)


def test_adapters_for_concatenation_includes_iqtree() -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    adapters = adapters_for_route(cfg, RouteId.concatenation)
    assert any(a.capability().tool_id == "iqtree2" for a in adapters)


def test_write_commands_script_uses_adapter_commands(tmp_path: Path) -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    workdir = tmp_path / "out"
    outputs_dir = tmp_path / "trees"
    concat = tmp_path / "concat.fasta"
    concat.write_text(">a\nACGT\n", encoding="utf-8")

    script = write_commands_script(
        cfg,
        RouteId.concatenation,
        workdir=workdir,
        outputs_dir=outputs_dir,
        loci_dir=None,
        concat_alignment=concat,
        loci_count=None,
    )
    text = script.read_text(encoding="utf-8")
    assert "iqtree2" in text
    assert "concatenated" in text
    assert "--prefix ../trees/concatenated" in text
    assert str(tmp_path) not in text


def test_iqtree_command_uses_configured_replicates_seed_and_quotes_paths(tmp_path: Path) -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    cfg.analysis.bootstrap_replicates = 42
    cfg.analysis.random_seed = 99
    adapter = _adapter(cfg, "iqtree2")
    commands = adapter.plan_commands(
        cfg,
        route=RouteId.concatenation,
        workdir=tmp_path / "output with spaces",
        loci_dir=None,
        concat_alignment=tmp_path / "input with spaces.fa",
        loci_count=2,
    )
    assert "-B 42" in commands[0].command
    assert "-seed 99" in commands[0].command
    assert f"'{tmp_path / 'input with spaces.fa'}'" in commands[0].command


def test_pargenes_command_uses_supported_configurable_options(tmp_path: Path) -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    cfg.execution.pargenes_bin = "custom-pargenes"
    cfg.execution.pargenes_cores = 6
    cfg.analysis.bootstrap_replicates = 42
    command = (
        _adapter(cfg, "pargenes")
        .plan_commands(
            cfg,
            route=RouteId.gene_tree,
            workdir=tmp_path / "output with spaces",
            loci_dir=tmp_path / "loci with spaces",
            concat_alignment=None,
            loci_count=cfg.analysis.large_locus_threshold,
        )[0]
        .command
    )

    assert "custom-pargenes" in command
    assert "-c 6" in command
    assert "-d nt" in command
    assert "-m" in command
    assert "-b 42" in command
    assert "-t 20" not in command
    assert "--use-ml-model" not in command
    assert f"'{tmp_path / 'loci with spaces'}'" in command


def test_large_gene_tree_script_contains_one_pargenes_command(tmp_path: Path) -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    cfg.analysis.large_locus_threshold = 1
    cfg.execution.pargenes_bin = "configured-pargenes"
    script = write_commands_script(
        cfg,
        RouteId.gene_tree,
        workdir=tmp_path / "commands",
        outputs_dir=tmp_path / "trees",
        loci_dir=tmp_path / "loci",
        concat_alignment=tmp_path / "concatenated.fasta",
        loci_count=2,
    )

    text = script.read_text(encoding="utf-8")
    assert text.count("configured-pargenes") == 1
    assert "--use-ml-model" not in text


def test_raxml_command_uses_configured_bootstraps_and_search_mode(tmp_path: Path) -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    cfg.execution.raxmlng_bin = "configured-raxml-ng"
    cfg.analysis.bootstrap_replicates = 42
    adapter = _adapter(cfg, "raxml-ng")
    command = adapter.plan_commands(
        cfg,
        route=RouteId.concatenation,
        workdir=tmp_path / "output with spaces",
        loci_dir=None,
        concat_alignment=tmp_path / "input with spaces.fa",
        loci_count=2,
    )[0].command
    assert "configured-raxml-ng --all" in command
    assert "--bs-trees 42" in command
    assert f"'{tmp_path / 'input with spaces.fa'}'" in command

    cfg.analysis.bootstrap_replicates = 0
    command = adapter.plan_commands(
        cfg,
        route=RouteId.concatenation,
        workdir=tmp_path / "output",
        loci_dir=None,
        concat_alignment=tmp_path / "input.fa",
        loci_count=2,
    )[0].command
    assert "configured-raxml-ng --search" in command
    assert "--bs-trees" not in command


def test_busco_guidance_uses_configured_binary_and_cores(tmp_path: Path) -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    cfg.execution.busco_bin = "configured-busco"
    cfg.execution.busco_cores = 7
    command = (
        _adapter(cfg, "busco")
        .plan_commands(
            cfg,
            route=RouteId.gene_tree,
            workdir=tmp_path,
            loci_dir=None,
            concat_alignment=None,
            loci_count=None,
        )[0]
        .command
    )
    assert "# configured-busco" in command
    assert "-c 7" in command
