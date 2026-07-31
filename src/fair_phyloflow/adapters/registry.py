from __future__ import annotations

from fair_phyloflow.adapters.base import ToolAdapter
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.domain import get_domain_pack
from fair_phyloflow.routes import RouteId


def default_adapters(cfg: WorkflowConfig) -> list[ToolAdapter]:
    return get_domain_pack(cfg).adapters(cfg)


def adapters_for_route(cfg: WorkflowConfig, route: RouteId) -> list[ToolAdapter]:
    return [a for a in default_adapters(cfg) if route in a.capability().routes]
