from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolStatus:
    name: str
    available: bool
    resolved_path: str | None


def which(tool: str) -> ToolStatus:
    p = shutil.which(tool)
    return ToolStatus(name=tool, available=p is not None, resolved_path=p)


def run_argv(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout: int | None = None,
) -> tuple[int, str]:
    """Execute an argument vector without a command shell."""

    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            shell=False,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return 124, stdout + ("\n" + stderr if stderr else "")
    except OSError as exc:
        return 127, str(exc)
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, out


def safe_run_version(cmd: list[str], *, timeout: int = 10) -> str | None:
    """Best-effort capture of a tool's version banner.

    Returns the first line (trimmed) or None if it cannot be obtained.
    """

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
            timeout=timeout,
        )  # noqa: S603
        if proc.returncode != 0:
            return None
        out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        if not out:
            return None
        return out.splitlines()[0][:200]
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
