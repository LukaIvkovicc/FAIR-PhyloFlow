from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from Bio import Phylo, SeqIO

from .config import WorkflowConfig
from .execution import run_argv, safe_run_version, which
from .provenance import sha256_file

TaskStatus = Literal[
    "planned",
    "running",
    "succeeded",
    "verified",
    "blocked",
    "failed",
    "interrupted",
    "invalid_output",
]

IQTREE_VERSION_SPEC = ">=2.2.2,<3"
RUN_PLAN_SCHEMA_VERSION = "1.1"


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    kind: str
    argv: list[str]
    cwd: str
    inputs: list[str]
    expected_outputs: list[str]
    depends_on: list[str] = field(default_factory=list)
    input_sha256: dict[str, str | None] = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        payload = {
            "task_id": self.task_id,
            "kind": self.kind,
            "argv": self.argv,
            "inputs": [{"path": path, "sha256": self.input_sha256.get(path)} for path in self.inputs],
            "expected_outputs": self.expected_outputs,
            "depends_on": self.depends_on,
        }
        return _digest(payload)


@dataclass(frozen=True)
class RunPlan:
    schema_version: str
    project_name: str
    created_at_utc: str
    config_path: str
    config_sha256: str
    run_dir: str
    backend: str
    required_version: str
    random_seed: int
    tasks: list[TaskSpec]

    @property
    def fingerprint(self) -> str:
        payload = asdict(self)
        payload.pop("created_at_utc", None)
        payload["tasks"] = [{**asdict(task), "fingerprint": task.fingerprint} for task in self.tasks]
        return _digest(payload)


@dataclass
class TaskState:
    task_id: str
    fingerprint: str
    status: TaskStatus
    started_at_utc: str | None = None
    finished_at_utc: str | None = None
    exit_code: int | None = None
    log_path: str | None = None
    outputs: dict[str, str] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionSummary:
    status: Literal["complete", "failed", "blocked"]
    run_dir: str
    plan_path: str
    state_path: str
    completed_tasks: int
    total_tasks: int
    message: str
    reason: Literal["external_tool", "run_state", "run_lock"] | None = None


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def _threads(cfg: WorkflowConfig) -> str:
    return str(cfg.analysis.threads)


def _input_hashes(paths: list[str]) -> dict[str, str | None]:
    return {path: sha256_file(Path(path)) if Path(path).is_file() else None for path in paths}


def build_run_id(cfg: WorkflowConfig, config_path: Path, selected_loci: list[Path]) -> str:
    """Return a stable identity for the configuration and selected evidence."""

    payload = {
        "config_sha256": sha256_file(config_path),
        "run_plan_schema": RUN_PLAN_SCHEMA_VERSION,
        "loci": [
            {"order": index, "name": path.name, "sha256": sha256_file(path)}
            for index, path in enumerate(selected_loci, start=1)
        ],
        "backend": cfg.execution.iqtree_bin,
        "version_spec": IQTREE_VERSION_SPEC,
        "threads": cfg.analysis.threads,
        "seed": cfg.analysis.random_seed,
        "bootstrap_replicates": cfg.analysis.bootstrap_replicates,
        "concordance_quartets": cfg.analysis.concordance_quartets,
    }
    return _digest(payload)[:12]


def build_run_plan(
    cfg: WorkflowConfig,
    *,
    config_path: Path,
    run_dir: Path,
    concatenated_alignment: Path,
    selected_loci: list[Path],
) -> RunPlan:
    """Create the immutable IQ-TREE task contract for one workflow run."""

    concatenated_alignment = concatenated_alignment.resolve()
    selected_loci = [path.resolve() for path in selected_loci]
    run_dir = run_dir.resolve()
    outputs = run_dir / "outputs"
    reference_dir = outputs / "reference"
    loci_dir = outputs / "loci"
    concordance_dir = outputs / "concordance"
    combined_trees = outputs / "gene_trees.nwk"
    binary = cfg.execution.iqtree_bin
    common = ["-T", _threads(cfg), "-seed", str(cfg.analysis.random_seed)]

    reference_prefix = reference_dir / "concatenated"
    reference_id = "reference_tree"
    reference_inputs = [str(concatenated_alignment)]
    bootstrap_args = ["-B", str(cfg.analysis.bootstrap_replicates)] if cfg.analysis.bootstrap_replicates > 0 else []
    reference = TaskSpec(
        task_id=reference_id,
        kind="iqtree_reference",
        argv=[
            binary,
            "-s",
            str(concatenated_alignment),
            "-m",
            "MFP",
            *bootstrap_args,
            *common,
            "--prefix",
            str(reference_prefix),
        ],
        cwd=str(reference_dir),
        inputs=reference_inputs,
        expected_outputs=[str(reference_prefix.with_suffix(".treefile")), str(reference_prefix.with_suffix(".iqtree"))],
        input_sha256=_input_hashes(reference_inputs),
    )

    locus_tasks: list[TaskSpec] = []
    for index, locus in enumerate(selected_loci, start=1):
        locus_id = f"locus_{index:04d}"
        prefix = loci_dir / locus_id / locus_id
        locus_inputs = [str(locus)]
        locus_tasks.append(
            TaskSpec(
                task_id=f"gene_tree_{locus_id}",
                kind="iqtree_gene_tree",
                argv=[
                    binary,
                    "-s",
                    str(locus),
                    "-m",
                    "MFP",
                    *common,
                    "--prefix",
                    str(prefix),
                ],
                cwd=str(prefix.parent),
                inputs=locus_inputs,
                expected_outputs=[str(prefix.with_suffix(".treefile")), str(prefix.with_suffix(".iqtree"))],
                input_sha256=_input_hashes(locus_inputs),
            )
        )

    combine = TaskSpec(
        task_id="combine_gene_trees",
        kind="combine_gene_trees",
        argv=[],
        cwd=str(outputs),
        inputs=[task.expected_outputs[0] for task in locus_tasks],
        expected_outputs=[str(combined_trees), str(outputs / "gene_tree_manifest.tsv")],
        depends_on=[task.task_id for task in locus_tasks],
        input_sha256={path: None for path in [task.expected_outputs[0] for task in locus_tasks]},
    )

    reference_tree = reference.expected_outputs[0]
    gcf_prefix = concordance_dir / "gcf"
    gcf = TaskSpec(
        task_id="gene_concordance",
        kind="iqtree_gcf",
        argv=[
            binary,
            "-t",
            reference_tree,
            "--gcf",
            str(combined_trees),
            "--prefix",
            str(gcf_prefix),
        ],
        cwd=str(concordance_dir),
        inputs=[reference_tree, str(combined_trees)],
        expected_outputs=[
            str(gcf_prefix.with_suffix(".cf.tree")),
            str(gcf_prefix.with_suffix(".cf.branch")),
            str(gcf_prefix.with_suffix(".cf.stat")),
        ],
        depends_on=[reference_id, combine.task_id],
        input_sha256={reference_tree: None, str(combined_trees): None},
    )

    scf_prefix = concordance_dir / "scf"
    scf = TaskSpec(
        task_id="site_concordance",
        kind="iqtree_scf",
        argv=[
            binary,
            "-t",
            reference_tree,
            "-s",
            str(concatenated_alignment),
            "--scf",
            str(cfg.analysis.concordance_quartets),
            *common,
            "--prefix",
            str(scf_prefix),
        ],
        cwd=str(concordance_dir),
        inputs=[reference_tree, str(concatenated_alignment)],
        expected_outputs=[
            str(scf_prefix.with_suffix(".cf.tree")),
            str(scf_prefix.with_suffix(".cf.branch")),
            str(scf_prefix.with_suffix(".cf.stat")),
        ],
        depends_on=[reference_id],
        input_sha256={reference_tree: None, str(concatenated_alignment): sha256_file(concatenated_alignment)},
    )
    normalized = TaskSpec(
        task_id="normalize_concordance",
        kind="normalize_concordance",
        argv=[],
        cwd=str(concordance_dir),
        inputs=[gcf.expected_outputs[-1], scf.expected_outputs[-1]],
        expected_outputs=[str(concordance_dir / "branch-summary.tsv")],
        depends_on=[gcf.task_id, scf.task_id],
        input_sha256={gcf.expected_outputs[-1]: None, scf.expected_outputs[-1]: None},
    )

    return RunPlan(
        schema_version=RUN_PLAN_SCHEMA_VERSION,
        project_name=cfg.project.name,
        created_at_utc=_now(),
        config_path=str(config_path.resolve()),
        config_sha256=sha256_file(config_path),
        run_dir=str(run_dir.resolve()),
        backend="iqtree2",
        required_version=IQTREE_VERSION_SPEC,
        random_seed=cfg.analysis.random_seed,
        tasks=[reference, *locus_tasks, combine, gcf, scf, normalized],
    )


def write_run_plan(plan: RunPlan, path: Path) -> Path:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("fingerprint") == plan.fingerprint:
            return path
        raise ValueError(f"Refusing to overwrite a different run plan: {path}")
    payload = asdict(plan)
    payload["fingerprint"] = plan.fingerprint
    payload["tasks"] = [{**asdict(task), "fingerprint": task.fingerprint} for task in plan.tasks]
    _write_json(path, payload)
    return path


def _version_tuple(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"\b(?:version\s*)?(\d+)\.(\d+)(?:\.(\d+))?", text, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)


def validate_iqtree_version(executable: str) -> tuple[bool, str]:
    status = which(executable)
    if not status.available:
        return False, f"IQ-TREE executable not found: {executable}"
    banner = safe_run_version([executable, "-version"])
    if banner is None:
        return False, f"Could not determine IQ-TREE version from: {executable}"
    version = _version_tuple(banner)
    if version is None:
        return False, f"Unrecognized IQ-TREE version banner: {banner}"
    if not ((2, 2, 2) <= version < (3, 0, 0)):
        return False, f"Unsupported IQ-TREE version {version}; required {IQTREE_VERSION_SPEC}"
    return True, banner


def validate_tree(tree_path: Path, alignment_path: Path | None = None) -> list[str]:
    errors: list[str] = []
    if not tree_path.is_file() or tree_path.stat().st_size == 0:
        return [f"Missing or empty tree: {tree_path}"]
    try:
        tree = Phylo.read(str(tree_path), "newick")
    except Exception as exc:
        return [f"Invalid Newick tree {tree_path}: {exc}"]
    labels = [str(clade.name) for clade in tree.get_terminals() if clade.name is not None]
    if len(labels) != len(set(labels)):
        errors.append(f"Tree has duplicate leaf labels: {tree_path}")
    if len(labels) < 3:
        errors.append(f"Tree has fewer than three labelled taxa: {tree_path}")
    if alignment_path is not None:
        alignment_taxa = {record.id for record in SeqIO.parse(str(alignment_path), "fasta")}
        unknown = sorted(set(labels) - alignment_taxa)
        missing = sorted(alignment_taxa - set(labels))
        if unknown:
            errors.append(f"Tree contains taxa absent from alignment: {', '.join(unknown)}")
        if missing:
            errors.append(f"Tree is missing alignment taxa: {', '.join(missing)}")
    return errors


def _validate_tabular_output(path: Path) -> list[str]:
    if not path.is_file() or path.stat().st_size == 0:
        return [f"Missing or empty concordance output: {path}"]
    first_line = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    if not any(name in first_line for name in ("gCF", "sCF", "ID", "Branch")):
        return [f"Concordance table has no recognized columns: {path}"]
    return []


def _task_validation(task: TaskSpec) -> list[str]:
    errors = [
        f"Missing or empty expected output: {path}"
        for path in task.expected_outputs
        if not Path(path).is_file() or Path(path).stat().st_size == 0
    ]
    if errors:
        return errors
    if task.kind in {"iqtree_reference", "iqtree_gene_tree"}:
        return validate_tree(Path(task.expected_outputs[0]), Path(task.inputs[0]))
    if task.kind in {"iqtree_gcf", "iqtree_scf"}:
        return _validate_tabular_output(Path(task.expected_outputs[-1]))
    return []


def _combine_gene_trees(task: TaskSpec) -> tuple[int, str]:
    output = Path(task.expected_outputs[0])
    manifest = Path(task.expected_outputs[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    tree_lines: list[str] = []
    manifest_lines = ["order\ttree_path\tsha256"]
    for index, source_text in enumerate(task.inputs, start=1):
        source = Path(source_text)
        if not source.is_file():
            return 5, f"Missing verified gene tree: {source}"
        tree_text = source.read_text(encoding="utf-8").strip()
        tree_lines.append(tree_text)
        manifest_lines.append(f"{index}\t{source}\t{sha256_file(source)}")
    output.write_text("\n".join(tree_lines) + "\n", encoding="utf-8")
    manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    return 0, f"Combined {len(tree_lines)} gene trees."


def _normalize_concordance(task: TaskSpec) -> tuple[int, str]:
    try:
        gcf = pd.read_csv(task.inputs[0], sep="\t")
        scf = pd.read_csv(task.inputs[1], sep="\t")
    except (OSError, pd.errors.ParserError) as exc:
        return 5, f"Could not parse concordance statistics: {exc}"
    if "ID" not in gcf.columns or "ID" not in scf.columns:
        return 5, "Both concordance tables must contain an ID column."
    gcf_columns = ["ID", *[column for column in gcf.columns if str(column).lower() == "gcf"]]
    scf_columns = ["ID", *[column for column in scf.columns if str(column).lower() == "scf"]]
    if len(gcf_columns) == 1 or len(scf_columns) == 1:
        return 5, "Expected gCF and sCF columns were not found."
    if gcf["ID"].isna().any() or scf["ID"].isna().any():
        return 5, "Concordance branch IDs must not be missing."
    if gcf["ID"].duplicated().any() or scf["ID"].duplicated().any():
        return 5, "Concordance branch IDs must be unique."
    if set(gcf["ID"]) != set(scf["ID"]):
        return 5, "gCF and sCF tables must contain the same branch IDs."
    gcf_value = gcf_columns[1]
    scf_value = scf_columns[1]
    gcf[gcf_value] = pd.to_numeric(gcf[gcf_value], errors="coerce")
    scf[scf_value] = pd.to_numeric(scf[scf_value], errors="coerce")
    if gcf[gcf_value].isna().any() or scf[scf_value].isna().any():
        return 5, "gCF and sCF values must be numeric."
    if not gcf[gcf_value].between(0, 100).all() or not scf[scf_value].between(0, 100).all():
        return 5, "gCF and sCF values must be within [0, 100]."
    merged = gcf[gcf_columns].merge(scf[scf_columns], on="ID", how="inner", validate="one_to_one")
    output = Path(task.expected_outputs[0])
    output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output, sep="\t", index=False)
    return 0, f"Normalized concordance evidence for {len(merged)} branches."


def _input_integrity_errors(plan: RunPlan) -> dict[str, list[str]]:
    errors: dict[str, list[str]] = {}
    for task in plan.tasks:
        task_errors: list[str] = []
        for path_text, expected in task.input_sha256.items():
            if expected is None:
                continue
            path = Path(path_text)
            if not path.is_file():
                task_errors.append(f"Input is missing: {path}")
            elif sha256_file(path) != expected:
                task_errors.append(f"Input checksum changed: {path}")
        if task_errors:
            errors[task.task_id] = task_errors
    return errors


def _resume_integrity_errors(plan: RunPlan, states: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    invalid: dict[str, list[str]] = {}
    for task in plan.tasks:
        prior = states.get(task.task_id)
        if not prior or prior.get("status") != "verified":
            continue
        errors: list[str] = []
        if prior.get("fingerprint") != task.fingerprint:
            errors.append("Task fingerprint changed.")
        errors.extend(_task_validation(task))
        recorded = prior.get("outputs", {})
        for output_text in task.expected_outputs:
            output = Path(output_text)
            expected_hash = recorded.get(output_text) if isinstance(recorded, dict) else None
            if expected_hash is None:
                errors.append(f"No recorded checksum for verified output: {output}")
            elif output.is_file() and sha256_file(output) != expected_hash:
                errors.append(f"Verified output checksum changed: {output}")
        if errors:
            invalid[task.task_id] = errors

    return _propagate_dependency_errors(plan, invalid)


def _propagate_dependency_errors(
    plan: RunPlan,
    invalid: dict[str, list[str]],
) -> dict[str, list[str]]:
    changed = True
    while changed:
        changed = False
        for task in plan.tasks:
            affected = [dependency for dependency in task.depends_on if dependency in invalid]
            if affected and task.task_id not in invalid:
                invalid[task.task_id] = [
                    f"Dependency integrity failed: {', '.join(affected)}",
                ]
                changed = True
    return invalid


def _acquire_run_lock(run_dir: Path) -> tuple[Path | None, str | None]:
    lock_path = run_dir / ".run.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "created_at_utc": _now(),
    }
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        try:
            owner = json.loads(lock_path.read_text(encoding="utf-8"))
            detail = f"pid={owner.get('pid')} host={owner.get('hostname')} since={owner.get('created_at_utc')}"
        except (OSError, json.JSONDecodeError):
            detail = "owner details unavailable"
            owner = {}
        owner_pid = owner.get("pid")
        if owner.get("hostname") == socket.gethostname() and isinstance(owner_pid, int):
            try:
                os.kill(owner_pid, 0)
            except ProcessLookupError:
                lock_path.unlink(missing_ok=True)
                return _acquire_run_lock(run_dir)
            except PermissionError:
                pass
        return None, f"Run is already locked ({detail}): {lock_path}"
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return lock_path, None


def _execute_run_plan_unlocked(plan: RunPlan, cfg: WorkflowConfig) -> ExecutionSummary:
    run_dir = Path(plan.run_dir)
    plan_path = run_dir / "run-plan.json"
    state_path = run_dir / "run-state.json"
    logs_dir = run_dir / "logs"
    write_run_plan(plan, plan_path)

    compatible, version_message = validate_iqtree_version(cfg.execution.iqtree_bin)
    if not compatible:
        _write_json(
            state_path,
            {
                "plan_fingerprint": plan.fingerprint,
                "status": "blocked",
                "message": version_message,
                "tasks": {},
            },
        )
        return ExecutionSummary(
            status="blocked",
            run_dir=str(run_dir),
            plan_path=str(plan_path),
            state_path=str(state_path),
            completed_tasks=0,
            total_tasks=len(plan.tasks),
            message=version_message,
            reason="external_tool",
        )

    existing: dict[str, Any] = {}
    if state_path.exists():
        existing = json.loads(state_path.read_text(encoding="utf-8"))
        if existing.get("plan_fingerprint") != plan.fingerprint:
            return ExecutionSummary(
                status="blocked",
                run_dir=str(run_dir),
                plan_path=str(plan_path),
                state_path=str(state_path),
                completed_tasks=0,
                total_tasks=len(plan.tasks),
                message="Existing run state does not match this plan.",
                reason="run_state",
            )
    states: dict[str, dict[str, Any]] = existing.get("tasks", {})

    input_errors = _propagate_dependency_errors(plan, _input_integrity_errors(plan))
    if input_errors:
        message = "Run inputs no longer match the immutable plan."
        for task_id, errors in input_errors.items():
            dependency_only = all(error.startswith("Dependency integrity failed") for error in errors)
            states[task_id] = asdict(
                TaskState(
                    task_id,
                    next(task.fingerprint for task in plan.tasks if task.task_id == task_id),
                    "blocked" if dependency_only else "invalid_output",
                )
            )
            states[task_id]["validation_errors"] = errors
        _write_json(
            state_path,
            {
                "plan_fingerprint": plan.fingerprint,
                "backend_version": version_message,
                "status": "failed",
                "message": message,
                "tasks": states,
            },
        )
        return ExecutionSummary("failed", str(run_dir), str(plan_path), str(state_path), 0, len(plan.tasks), message)

    integrity_errors = _resume_integrity_errors(plan, states)
    if integrity_errors:
        for task in plan.tasks:
            if task.task_id not in integrity_errors:
                continue
            direct_failure = not all(
                error.startswith("Dependency integrity failed") for error in integrity_errors[task.task_id]
            )
            state = TaskState(
                task.task_id,
                task.fingerprint,
                "invalid_output" if direct_failure else "blocked",
                validation_errors=integrity_errors[task.task_id],
            )
            states[task.task_id] = asdict(state)
        message = "Previously verified evidence changed; affected tasks were recursively invalidated."
        _write_json(
            state_path,
            {
                "plan_fingerprint": plan.fingerprint,
                "backend_version": version_message,
                "status": "failed",
                "message": message,
                "tasks": states,
            },
        )
        completed = sum(item.get("status") == "verified" for item in states.values())
        return ExecutionSummary(
            "failed", str(run_dir), str(plan_path), str(state_path), completed, len(plan.tasks), message
        )

    for task in plan.tasks:
        prior = states.get(task.task_id)
        if prior and prior.get("fingerprint") == task.fingerprint and prior.get("status") == "verified":
            if not _task_validation(task):
                continue
        unmet = [dep for dep in task.depends_on if states.get(dep, {}).get("status") != "verified"]
        if unmet:
            message = f"Task {task.task_id} blocked by incomplete dependencies: {', '.join(unmet)}"
            states[task.task_id] = asdict(TaskState(task.task_id, task.fingerprint, "blocked"))
            _write_json(
                state_path,
                {
                    "plan_fingerprint": plan.fingerprint,
                    "backend_version": version_message,
                    "status": "blocked",
                    "message": message,
                    "tasks": states,
                },
            )
            return ExecutionSummary(
                "blocked", str(run_dir), str(plan_path), str(state_path), 0, len(plan.tasks), message, "run_state"
            )

        cwd = Path(task.cwd)
        cwd.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / f"{task.task_id}.log"
        state = TaskState(task.task_id, task.fingerprint, "running", started_at_utc=_now(), log_path=str(log_path))
        states[task.task_id] = asdict(state)
        _write_json(
            state_path,
            {
                "plan_fingerprint": plan.fingerprint,
                "backend_version": version_message,
                "status": "running",
                "tasks": states,
            },
        )

        if task.kind == "combine_gene_trees":
            code, output = _combine_gene_trees(task)
        elif task.kind == "normalize_concordance":
            code, output = _normalize_concordance(task)
        else:
            code, output = run_argv(
                task.argv,
                cwd=cwd,
                timeout=cfg.execution.command_timeout_seconds,
            )
        log_path.write_text(output, encoding="utf-8")
        errors = [] if code == 0 else [f"Command exited with code {code}"]
        if not errors:
            errors = _task_validation(task)
        status: TaskStatus = "verified" if not errors else ("invalid_output" if code == 0 else "failed")
        state.status = status
        state.exit_code = code
        state.finished_at_utc = _now()
        state.validation_errors = errors
        if status == "verified":
            state.outputs = {path: sha256_file(Path(path)) for path in task.expected_outputs}
        states[task.task_id] = asdict(state)
        overall = "running" if status == "verified" else "failed"
        _write_json(
            state_path,
            {
                "plan_fingerprint": plan.fingerprint,
                "backend_version": version_message,
                "status": overall,
                "tasks": states,
            },
        )
        if status != "verified":
            completed = sum(item.get("status") == "verified" for item in states.values())
            return ExecutionSummary(
                "failed",
                str(run_dir),
                str(plan_path),
                str(state_path),
                completed,
                len(plan.tasks),
                f"Task {task.task_id} failed validation: {'; '.join(errors)}",
            )

    _write_json(
        state_path,
        {
            "plan_fingerprint": plan.fingerprint,
            "backend_version": version_message,
            "status": "complete",
            "completed_at_utc": _now(),
            "tasks": states,
        },
    )
    return ExecutionSummary(
        "complete",
        str(run_dir),
        str(plan_path),
        str(state_path),
        len(plan.tasks),
        len(plan.tasks),
        "All tasks completed and passed output validation.",
    )


def execute_run_plan(plan: RunPlan, cfg: WorkflowConfig) -> ExecutionSummary:
    run_dir = Path(plan.run_dir)
    lock_path, lock_error = _acquire_run_lock(run_dir)
    if lock_path is None:
        return ExecutionSummary(
            "blocked",
            str(run_dir),
            str(run_dir / "run-plan.json"),
            str(run_dir / "run-state.json"),
            0,
            len(plan.tasks),
            lock_error or "Run is locked.",
            "run_lock",
        )
    try:
        return _execute_run_plan_unlocked(plan, cfg)
    finally:
        lock_path.unlink(missing_ok=True)
