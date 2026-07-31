from pathlib import Path

from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.domain import get_domain_pack


def test_phylogenomics_domain_pack_declares_identity_and_adapters() -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    pack = get_domain_pack(cfg)
    assert pack.metadata().pack_id == "phylogenomics"
    assert pack.metadata().configuration_version == "1"
    assert any(adapter.capability().tool_id == "iqtree2" for adapter in pack.adapters(cfg))
