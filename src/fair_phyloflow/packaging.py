from __future__ import annotations

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from . import PRODUCT_NAME
from .provenance import sha256_file

REQUIRED_PACKAGE_FILES = {
    "project.snapshot.json",
    "provenance.json",
    "report.html",
    "report.md",
}


def _copy_if_distinct(src: Path, dst: Path) -> None:
    if src.resolve() == dst.resolve():
        return
    shutil.copy2(src, dst)


def package_fair_outputs(
    *,
    outdir: Path,
    report_md: Path,
    report_html: Path,
    provenance_json: Path,
    commands_script: Path | None,
    extra_paths: list[Path] | None = None,
) -> Path:
    pkg = outdir / "07_fair_package"
    outdir.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".fair-package-", dir=outdir))
    try:
        _copy_if_distinct(report_md, temporary / "report.md")
        _copy_if_distinct(report_html, temporary / "report.html")
        _copy_if_distinct(provenance_json, temporary / "provenance.json")
        if commands_script is not None and commands_script.exists():
            _copy_if_distinct(commands_script, temporary / "reproducible_commands.sh")

        for p in extra_paths or []:
            if not p.exists():
                continue
            if p.is_dir():
                target = temporary / p.name
                if p.name == "08_runs":
                    _copy_latest_run(p, target)
                else:
                    shutil.copytree(p, target)
            else:
                _copy_if_distinct(p, temporary / p.name)
        write_checksum_manifest(temporary)
        write_ro_crate_metadata(temporary)
        errors = verify_fair_package(temporary)
        if errors:
            raise ValueError("Generated FAIR package failed verification: " + "; ".join(errors))

        backup = Path(tempfile.mkdtemp(prefix=".fair-package-backup-", dir=outdir))
        backup.rmdir()
        try:
            if pkg.exists():
                pkg.rename(backup)
            temporary.rename(pkg)
        except OSError:
            if backup.exists() and not pkg.exists():
                backup.rename(pkg)
            raise
        if backup.exists():
            shutil.rmtree(backup)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return pkg


def _copy_latest_run(runs_dir: Path, target: Path) -> None:
    """Copy only the run selected by latest-run.json into an evidence package."""

    latest_path = runs_dir / "latest-run.json"
    if not latest_path.is_file():
        return
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    run_id = latest.get("run_id")
    if not isinstance(run_id, str) or Path(run_id).name != run_id:
        raise ValueError("latest-run.json contains an invalid run_id")
    source_run = runs_dir / run_id
    if not source_run.is_dir():
        raise ValueError(f"Latest run directory is missing: {source_run}")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest_path, target / latest_path.name)
    packaged_run = target / run_id
    shutil.copytree(source_run, packaged_run)
    _make_packaged_run_portable(packaged_run, source_run)


def _portable_json_value(value: object, run_root: Path) -> object:
    if isinstance(value, dict):
        return {
            str(_portable_json_value(key, run_root)): _portable_json_value(item, run_root)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_portable_json_value(item, run_root) for item in value]
    if not isinstance(value, str):
        return value
    path = Path(value)
    if not path.is_absolute():
        return value
    try:
        relative = path.relative_to(run_root)
        return f"${{RUN_DIR}}/{relative.as_posix()}" if relative.parts else "${RUN_DIR}"
    except ValueError:
        return path.name


def _make_packaged_run_portable(packaged_run: Path, source_run: Path) -> None:
    """Redact machine-specific roots in the packaged copy, preserving source evidence."""

    for path in packaged_run.rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        portable = _portable_json_value(value, source_run)
        if path.name == "run-plan.json" and isinstance(portable, dict):
            portable["packaged_path_policy"] = {
                "run_root_token": "${RUN_DIR}",
                "external_absolute_paths": "basename_only",
                "fingerprints": "preserved_from_execution_record",
            }
        path.write_text(json.dumps(portable, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for pattern in ("*.tsv", "*.log", "*.txt", "*.sh", "*.md"):
        for path in packaged_run.rglob(pattern):
            text = path.read_text(encoding="utf-8", errors="replace")
            path.write_text(text.replace(str(source_run), "${RUN_DIR}"), encoding="utf-8")


def write_checksum_manifest(package_dir: Path) -> Path:
    """Write a deterministic SHA-256 inventory of packaged evidence."""

    manifest = package_dir / "manifest-sha256.tsv"
    rows = ["path\tbytes\tsha256"]
    for path in sorted(package_dir.rglob("*")):
        if not path.is_file() or path in {manifest, package_dir / "ro-crate-metadata.json"}:
            continue
        relative = path.relative_to(package_dir).as_posix()
        rows.append(f"{relative}\t{path.stat().st_size}\t{sha256_file(path)}")
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return manifest


def write_ro_crate_metadata(package_dir: Path) -> Path:
    """Write a compact RO-Crate-compatible metadata graph for the package."""

    manifest = package_dir / "manifest-sha256.tsv"
    files = [
        {
            "@id": path.relative_to(package_dir).as_posix(),
            "@type": "File",
            "contentSize": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(package_dir.rglob("*"))
        if path.is_file() and path.name != "ro-crate-metadata.json"
    ]
    graph: list[dict[str, object]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": {"@id": "./"},
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": f"{PRODUCT_NAME} evidence package",
            "datePublished": datetime.now(UTC).isoformat(),
            "hasPart": [{"@id": item["@id"]} for item in files],
            "mainEntity": {"@id": manifest.relative_to(package_dir).as_posix()},
        },
        *files,
    ]
    metadata = {"@context": "https://w3id.org/ro/crate/1.1/context", "@graph": graph}
    output = package_dir / "ro-crate-metadata.json"
    output.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def verify_fair_package(package_dir: Path) -> list[str]:
    """Return integrity/schema errors for a FAIR PhyloFlow package."""

    errors: list[str] = []
    manifest = package_dir / "manifest-sha256.tsv"
    crate = package_dir / "ro-crate-metadata.json"
    if not package_dir.is_dir():
        return [f"Package directory does not exist: {package_dir}"]
    for required in sorted(REQUIRED_PACKAGE_FILES):
        if not (package_dir / required).is_file():
            errors.append(f"Missing required package file: {required}")
    if not manifest.is_file():
        errors.append("Missing manifest-sha256.tsv")
    else:
        lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines or lines[0] != "path\tbytes\tsha256":
            errors.append("Checksum manifest has an invalid header.")
        seen: set[str] = set()
        for line_number, line in enumerate(lines[1:], start=2):
            fields = line.split("\t")
            if len(fields) != 3:
                errors.append(f"Malformed checksum row at line {line_number}.")
                continue
            relative, expected_size_text, expected_hash = fields
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                errors.append(f"Unsafe manifest path: {relative}")
                continue
            if relative in seen:
                errors.append(f"Duplicate manifest path: {relative}")
                continue
            seen.add(relative)
            evidence = package_dir / relative_path
            if not evidence.is_file():
                errors.append(f"Missing packaged file: {relative}")
                continue
            try:
                expected_size = int(expected_size_text)
            except ValueError:
                errors.append(f"Invalid byte count for {relative}: {expected_size_text}")
                continue
            if evidence.stat().st_size != expected_size:
                errors.append(f"Size mismatch for {relative}")
            if sha256_file(evidence) != expected_hash:
                errors.append(f"Checksum mismatch for {relative}")

        actual = {
            path.relative_to(package_dir).as_posix()
            for path in package_dir.rglob("*")
            if path.is_file() and path not in {manifest, crate}
        }
        for relative in sorted(actual - seen):
            errors.append(f"Unlisted packaged file: {relative}")
        for relative in sorted(seen - actual):
            if (package_dir / relative).is_file():
                continue
            errors.append(f"Manifest entry has no file: {relative}")

    if not crate.is_file():
        errors.append("Missing ro-crate-metadata.json")
    else:
        try:
            metadata = json.loads(crate.read_text(encoding="utf-8"))
            graph = metadata.get("@graph")
            if metadata.get("@context") != "https://w3id.org/ro/crate/1.1/context":
                errors.append("RO-Crate context is missing or unsupported.")
            if not isinstance(graph, list) or not any(
                isinstance(item, dict) and item.get("@id") == "./" and item.get("@type") == "Dataset" for item in graph
            ):
                errors.append("RO-Crate dataset entity is missing.")
            if isinstance(graph, list):
                crate_files: set[str] = set()
                for entity in graph:
                    if not isinstance(entity, dict) or entity.get("@type") != "File":
                        continue
                    identifier = entity.get("@id")
                    if not isinstance(identifier, str):
                        errors.append("RO-Crate file entity has no valid @id.")
                        continue
                    crate_relative = Path(identifier)
                    if crate_relative.is_absolute() or ".." in crate_relative.parts:
                        errors.append(f"Unsafe RO-Crate file path: {identifier}")
                        continue
                    if identifier in crate_files:
                        errors.append(f"Duplicate RO-Crate file entity: {identifier}")
                        continue
                    crate_files.add(identifier)
                    evidence = package_dir / crate_relative
                    if not evidence.is_file():
                        errors.append(f"RO-Crate file entity is missing: {identifier}")
                        continue
                    if entity.get("contentSize") != evidence.stat().st_size:
                        errors.append(f"RO-Crate size mismatch for {identifier}")
                    if entity.get("sha256") != sha256_file(evidence):
                        errors.append(f"RO-Crate checksum mismatch for {identifier}")
                actual_crate_files = {
                    path.relative_to(package_dir).as_posix()
                    for path in package_dir.rglob("*")
                    if path.is_file() and path != crate
                }
                for identifier in sorted(actual_crate_files - crate_files):
                    errors.append(f"File is absent from RO-Crate metadata: {identifier}")
                for identifier in sorted(crate_files - actual_crate_files):
                    errors.append(f"RO-Crate metadata lists an absent file: {identifier}")
        except (OSError, json.JSONDecodeError):
            errors.append("RO-Crate metadata is not valid JSON.")
    return errors
