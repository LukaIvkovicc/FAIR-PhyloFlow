from __future__ import annotations

from dataclasses import dataclass

from .adapters.registry import default_adapters
from .config import WorkflowConfig


@dataclass(frozen=True)
class ToolStatusRow:
    tool_id: str
    label: str
    routes: str
    support_level: str
    available: bool
    path: str | None
    version: str | None


def collect_tool_status(cfg: WorkflowConfig) -> list[ToolStatusRow]:
    rows: list[ToolStatusRow] = []
    for adapter in default_adapters(cfg):
        cap = adapter.capability()
        ver = adapter.version(cfg)
        routes = ",".join(sorted(route.value for route in cap.routes))
        rows.append(
            ToolStatusRow(
                tool_id=cap.tool_id,
                label=cap.label,
                routes=routes,
                support_level=cap.support.value,
                available=ver.available,
                path=ver.path,
                version=ver.version,
            )
        )
    return rows
