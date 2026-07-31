from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import DOMAIN_DISTRIBUTION_NAME, PRODUCT_NAME, __version__
from .adapters.registry import default_adapters
from .config import WorkflowConfig
from .execution import run_argv, safe_run_version, which


@dataclass(frozen=True)
class Provenance:
    created_at_utc: str
    product_name: str
    domain_pack: str
    distribution_name: str
    fair_phyloflow_version: str
    python: dict[str, str]
    platform: dict[str, str]
    git: dict[str, str | bool | None]
    config_sha256: str
    tools: dict[str, dict[str, str | bool | None]]
    adapters: list[dict[str, str | bool | None]]
    commands_script: str | None


def _git_info() -> dict[str, str | bool | None]:
    g = which("git")
    if not g.available:
        return {"available": False, "path": None, "commit": None, "dirty": None}

    commit_code, commit_output = run_argv(["git", "rev-parse", "HEAD"])
    status_code, status_output = run_argv(["git", "status", "--porcelain"])
    commit = commit_output.strip().splitlines()[0] if commit_code == 0 and commit_output.strip() else None
    dirty = bool(status_output.strip()) if status_code == 0 else None
    return {
        "available": True,
        "path": Path(g.resolved_path).name if g.resolved_path else None,
        "commit": commit,
        "dirty": dirty,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_provenance(*, config_path: Path, commands_script: Path | None) -> Provenance:
    cfg = WorkflowConfig.load(config_path)
    iqtree_executable = cfg.execution.iqtree_bin
    iq = which(iqtree_executable)

    iq_version: str | None = None
    if iq.available:
        # IQ-TREE supports `-version` (prints version info and exits)
        iq_version = safe_run_version([iqtree_executable, "-version"])

    tools = {
        iqtree_executable: {
            "available": iq.available,
            "path": Path(iq.resolved_path).name if iq.resolved_path else None,
            "version": iq_version,
        },
    }

    adapters = []
    for adapter in default_adapters(cfg):
        version = adapter.version(cfg)
        adapters.append(
            {
                **version.__dict__,
                "path": Path(version.path).name if version.path else None,
            }
        )

    return Provenance(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        product_name=PRODUCT_NAME,
        domain_pack=cfg.domain_pack,
        distribution_name=DOMAIN_DISTRIBUTION_NAME,
        fair_phyloflow_version=__version__,
        python={
            "version": sys.version.replace("\n", " "),
            "executable": Path(sys.executable).name,
            "implementation": platform.python_implementation(),
        },
        platform={
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        git=_git_info(),
        config_sha256=sha256_file(config_path),
        tools=tools,
        adapters=adapters,
        commands_script=commands_script.name if commands_script else None,
    )


def write_provenance_json(prov: Provenance, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(prov.__dict__, indent=2), encoding="utf-8")
    return out_path
