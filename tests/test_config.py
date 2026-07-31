from pathlib import Path

import pytest
from pydantic import ValidationError

from fair_phyloflow.config import WorkflowConfig


def test_load_demo_config() -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    assert cfg.project.name
    assert cfg.input.mode.value == "locus_alignments"
    assert cfg.input.data_type is not None
    assert cfg.input.data_type.value == "locus_alignments"
    assert cfg.input.alignments_dir == Path("examples/demo_project/alignments").resolve()
    assert cfg.input.taxa_table == Path("examples/demo_project/taxa.tsv").resolve()
    assert cfg.project.outdir == Path("results/demo_project").resolve()
    assert cfg.execution.pargenes_cores == 2
    assert cfg.execution.busco_cores == 1


def test_execution_version_requirement_cannot_be_overridden(tmp_path: Path) -> None:
    config = tmp_path / "project.yaml"
    config.write_text(
        "project: {name: x}\n"
        "question: {type: broad_relationship_inference}\n"
        "input: {mode: locus_alignments, alignments_dir: .}\n"
        "execution: {iqtree_version_spec: '>=1'}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        WorkflowConfig.load(config)


@pytest.mark.parametrize(
    "fragment",
    [
        "unknown_section: true\n",
        "analysis: {threads: 0}\n",
        "analysis: {threads: fastest}\n",
        "analysis: {max_mean_missing_fraction: 1.1}\n",
        "analysis: {route: concatenation, allow_concatenation: false}\n",
        "input: {mode: locus_alignments, data_type: raw_reads, alignments_dir: .}\n",
        "fair: {capture_provenance: false}\n",
        "domain_pack: proteomics\n",
        "execution: {mode: conda}\n",
        "execution: {pargenes_cores: 1}\n",
        "execution: {busco_cores: 0}\n",
    ],
)
def test_invalid_or_misleading_configuration_is_rejected(tmp_path: Path, fragment: str) -> None:
    config = tmp_path / "project.yaml"
    base = (
        "project: {name: x}\n"
        "question: {type: broad_relationship_inference}\n"
        "input: {mode: locus_alignments, alignments_dir: .}\n"
    )
    if fragment.startswith("input:"):
        base = "project: {name: x}\nquestion: {type: broad_relationship_inference}\n"
    config.write_text(base + fragment, encoding="utf-8")
    with pytest.raises(ValidationError):
        WorkflowConfig.load(config)
