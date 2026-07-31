from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Protocol

from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.execution import ToolStatus
from fair_phyloflow.routes import RouteId


class SupportLevel(str, Enum):
    guided = "guided"  # explains requirements/choices
    command = "command"  # generates reproducible commands
    executable = "executable"  # can run directly in the current process environment
    parsed = "parsed"  # outputs can be parsed/interpreted


@dataclass(frozen=True)
class AdapterCapability:
    tool_id: str
    label: str
    routes: set[RouteId]
    support: SupportLevel


@dataclass(frozen=True)
class PlannedCommand:
    label: str
    command: str
    cwd: Path | None = None


@dataclass(frozen=True)
class ToolVersion:
    tool_id: str
    available: bool
    path: str | None
    version: str | None


class ToolAdapter(Protocol):
    def capability(self) -> AdapterCapability: ...

    def detect(self, cfg: WorkflowConfig) -> ToolStatus: ...

    def version(self, cfg: WorkflowConfig) -> ToolVersion: ...

    def plan_commands(
        self,
        cfg: WorkflowConfig,
        *,
        route: RouteId,
        workdir: Path,
        loci_dir: Path | None,
        concat_alignment: Path | None,
        loci_count: int | None,
    ) -> list[PlannedCommand]: ...
