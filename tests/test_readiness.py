from pathlib import Path

from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.readiness import assess_readiness


def test_readiness_demo_is_not_ready_or_caution() -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    res = assess_readiness(cfg)
    assert res.status in {"ready", "caution", "not_ready"}


def test_readiness_warns_when_outgroup_missing_from_accessions() -> None:
    cfg = WorkflowConfig.load(Path("examples/penicillium_camemberti_case/project.yaml"))
    res = assess_readiness(cfg)

    assert res.status == "caution"
    assert any("Declared outgroup not found in accessions table" in w for w in res.warnings)
