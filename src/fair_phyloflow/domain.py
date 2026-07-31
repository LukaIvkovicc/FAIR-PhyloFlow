from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .adapters.base import ToolAdapter
    from .config import WorkflowConfig


@dataclass(frozen=True)
class DomainPackMetadata:
    pack_id: str
    label: str
    description: str
    configuration_version: str


class DomainPack(Protocol):
    def metadata(self) -> DomainPackMetadata: ...

    def adapters(self, cfg: WorkflowConfig) -> list[ToolAdapter]: ...


def get_domain_pack(cfg: WorkflowConfig) -> DomainPack:
    """Resolve the configured scientific domain without coupling the core to its tools."""

    if cfg.domain_pack == "phylogenomics":
        from .domains.phylogenomics import PhylogenomicsDomainPack

        return PhylogenomicsDomainPack()
    raise ValueError(f"Unsupported domain pack: {cfg.domain_pack}")
