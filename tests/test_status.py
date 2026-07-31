from pathlib import Path

from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.status import collect_tool_status


def test_collect_tool_status_includes_expected_adapters() -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    rows = collect_tool_status(cfg)
    tool_ids = {row.tool_id for row in rows}

    assert "iqtree2" in tool_ids
    assert "pargenes" in tool_ids
    assert "busco" in tool_ids
