from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from . import PRODUCT_NAME, __version__
from .commands import write_commands_script
from .concatenate import concatenate_alignments
from .concordance import interpret_iqtree_concordance
from .config import WorkflowConfig
from .execution import run_argv, which
from .iqtree_results import summarize_iqtree_run
from .loci import classify_loci_for_selection, compute_locus_metrics
from .packaging import package_fair_outputs, verify_fair_package
from .provenance import build_provenance, sha256_file, write_provenance_json
from .readiness import assess_readiness
from .reporting import write_html_report, write_markdown_report
from .resources import (
    load_curated_accessions_table,
    summarize_accessions,
    write_accessions_normalized_tsv,
    write_accessions_registry_json,
)
from .routes import recommend_route
from .run_contract import build_run_id, build_run_plan, execute_run_plan, write_run_plan
from .status import collect_tool_status

app = typer.Typer(add_completion=False)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the FAIR PhyloFlow version and exit.", is_eager=True),
    ] = False,
) -> None:
    """Decision-aware, reproducible phylogenomics with transparent provenance."""

    if version:
        console.print(f"{PRODUCT_NAME} {__version__}")
        raise typer.Exit()


def _stage_dir(cfg: WorkflowConfig, stage: str) -> Path:
    return cfg.project.outdir / stage


def _load_config(config_path: Path) -> WorkflowConfig:
    """Load a project configuration under the documented CLI exit contract."""

    try:
        return WorkflowConfig.load(config_path)
    except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(code=2) from exc


def _public_source_label(path: Path, config_path: Path) -> str:
    """Return a useful source label without embedding private absolute paths."""

    try:
        return path.resolve().relative_to(config_path.resolve().parent).as_posix()
    except ValueError:
        return path.name


def _selected_locus_paths(cfg: WorkflowConfig, loci_df: pd.DataFrame) -> list[Path]:
    if cfg.input.alignments_dir is None:
        return []
    return [
        path if path.is_absolute() else cfg.input.alignments_dir / path
        for path in (Path(value) for value in loci_df.loc[loci_df["selected"], "file"].tolist())
    ]


@app.command()
def check(config_path: Path) -> None:
    """Validate config and run basic readiness checks."""
    cfg = _load_config(config_path)
    readiness = assess_readiness(cfg)
    console.print(f"Readiness: [bold]{readiness.status}[/bold]")
    for i in readiness.issues:
        console.print(f"[red]Issue[/red]: {i}")
    for w in readiness.warnings:
        console.print(f"[yellow]Warning[/yellow]: {w}")
    raise typer.Exit(code=0 if readiness.status != "not_ready" else 2)


@app.command()
def status(config_path: Path) -> None:
    """Show route-aware tool adapter status for this project."""
    cfg = _load_config(config_path)
    rows = collect_tool_status(cfg)

    table = Table(title=f"{PRODUCT_NAME} · Phylogenomics tool status: {cfg.project.name}")
    table.add_column("Tool")
    table.add_column("Routes")
    table.add_column("Support")
    table.add_column("Available")
    table.add_column("Path / Version")

    for row in rows:
        available = "yes" if row.available else "no"
        detail = row.path or "-"
        if row.version:
            detail = f"{detail}\n{row.version}"
        table.add_row(row.label, row.routes, row.support_level, available, detail)

    console.print(table)
    console.print(
        "\nSupport levels: guided = documented guidance; command = reproducible commands; "
        "executable = can run directly; parsed = outputs can be interpreted."
    )


@app.command()
def plan(config_path: Path) -> None:
    """Compute locus metrics (if alignments provided) and recommend a route."""
    cfg = _load_config(config_path)
    readiness = assess_readiness(cfg)

    # Stage 2: curated resources (accessions-first)
    if cfg.input.accessions_table is not None:
        df = load_curated_accessions_table(cfg.input.accessions_table)
        stage2 = _stage_dir(cfg, "02_resources")
        norm_path = stage2 / "accessions_normalized.tsv"
        reg_path = stage2 / "resource_registry.json"
        write_accessions_normalized_tsv(df, norm_path)
        summary = summarize_accessions(df, source_path=cfg.input.accessions_table, outgroup=cfg.input.outgroup)
        write_accessions_registry_json(summary, reg_path)
        console.print(f"Wrote curated accessions: {norm_path}")
        console.print(f"Wrote resource registry: {reg_path}")

    loci_df: pd.DataFrame | None = None
    loci_count: int | None = None
    if cfg.input.alignments_dir and cfg.input.alignments_dir.exists():
        loci_df = classify_loci_for_selection(compute_locus_metrics(cfg.input.alignments_dir), cfg)
        loci_count = int(loci_df["selected"].sum()) if "selected" in loci_df.columns else int(len(loci_df))
        stage3 = _stage_dir(cfg, "03_loci")
        out_metrics = stage3 / "locus_metrics.tsv"
        out_selected = stage3 / "selected_loci.tsv"
        out_excluded = stage3 / "excluded_loci.tsv"
        stage3.mkdir(parents=True, exist_ok=True)
        loci_df.to_csv(out_metrics, sep="\t", index=False)
        loci_df[loci_df["selected"]].to_csv(out_selected, sep="\t", index=False)
        loci_df[~loci_df["selected"]].to_csv(out_excluded, sep="\t", index=False)
        console.print(f"Wrote locus metrics: {out_metrics}")
        console.print(f"Wrote selected loci: {out_selected}")
        console.print(f"Wrote excluded loci: {out_excluded}")

    rec = recommend_route(cfg, loci_count=loci_count)
    out_route = _stage_dir(cfg, "04_route") / "recommended_route.txt"
    out_route.parent.mkdir(parents=True, exist_ok=True)
    out_route.write_text(
        "\n".join(
            [
                f"route={rec.route.value}",
                "rationale:",
                *[f"- {r}" for r in rec.rationale],
                "warnings:",
                *[f"- {w}" for w in rec.warnings],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    console.print(f"Recommended route: [bold]{rec.route.value}[/bold]")
    for r in rec.rationale:
        console.print(f"- {r}")
    for w in rec.warnings:
        console.print(f"[yellow]- {w}[/yellow]")

    if readiness.status == "not_ready":
        raise typer.Exit(code=2)


@app.command()
def run(config_path: Path, execute: bool = typer.Option(True, "--execute/--no-execute")) -> None:
    """Generate commands and optionally execute IQ-TREE if available."""
    cfg = _load_config(config_path)
    readiness = assess_readiness(cfg)
    if readiness.status == "not_ready":
        console.print("[red]Not ready; fix issues then re-run.[/red]")
        raise typer.Exit(code=2)

    loci_df: pd.DataFrame | None = None
    loci_count: int | None = None
    if cfg.input.alignments_dir and cfg.input.alignments_dir.exists():
        loci_df = classify_loci_for_selection(compute_locus_metrics(cfg.input.alignments_dir), cfg)
        loci_count = int(loci_df["selected"].sum()) if "selected" in loci_df.columns else int(len(loci_df))

    rec = recommend_route(cfg, loci_count=loci_count)

    concat_alignment: Path | None = None
    command_loci_dir = cfg.input.alignments_dir
    if cfg.input.alignments_dir:
        concat_alignment = _stage_dir(cfg, "05_trees") / "concatenated_alignment.fasta"
        selected_loci = None
        if loci_df is not None and "selected" in loci_df.columns:
            selected_loci = _selected_locus_paths(cfg, loci_df)
            selected_loci_dir = _stage_dir(cfg, "05_trees") / "selected_loci_alignments"
            selected_loci_dir.mkdir(parents=True, exist_ok=True)
            for old in list(selected_loci_dir.glob("*.fa")) + list(selected_loci_dir.glob("*.fasta")):
                old.unlink()
            for locus_path in selected_loci:
                shutil.copy2(locus_path, selected_loci_dir / locus_path.name)
            command_loci_dir = selected_loci_dir
        concatenate_alignments(cfg.input.alignments_dir, concat_alignment, loci_paths=selected_loci)
        console.print(f"Wrote concatenated alignment: {concat_alignment}")

    cmd_dir = _stage_dir(cfg, "04_route")
    commands_script = write_commands_script(
        cfg,
        rec.route,
        workdir=cmd_dir,
        outputs_dir=_stage_dir(cfg, "05_trees"),
        loci_dir=command_loci_dir,
        concat_alignment=concat_alignment,
        loci_count=loci_count,
    )
    console.print(f"Wrote commands: {commands_script}")

    iq = which(cfg.execution.iqtree_bin)
    if execute and cfg.execution.execute_when_available and iq.available:
        console.print(f"Executing IQ-TREE via: {iq.resolved_path}")
        if concat_alignment is not None:
            argv = [
                cfg.execution.iqtree_bin,
                "-s",
                str(concat_alignment),
                "-m",
                "MFP",
            ]
            if cfg.analysis.bootstrap_replicates > 0:
                argv.extend(["-B", str(cfg.analysis.bootstrap_replicates)])
            argv.extend(
                [
                    "-T",
                    str(cfg.analysis.threads),
                    "-seed",
                    str(cfg.analysis.random_seed),
                    "--prefix",
                    str(_stage_dir(cfg, "05_trees") / "concatenated"),
                ]
            )
            code, out = run_argv(
                argv,
                cwd=_stage_dir(cfg, "05_trees"),
                timeout=cfg.execution.command_timeout_seconds,
            )
            (_stage_dir(cfg, "05_trees") / "iqtree_run.log").write_text(out, encoding="utf-8")
            console.print(f"IQ-TREE exit code: {code}")
            if code != 0:
                raise typer.Exit(code=5)
    else:
        console.print("Skipping execution (IQ-TREE not available or execution disabled).")


@app.command(name="execute")
def execute_route(
    config_path: Path,
    plan_only: bool = typer.Option(False, "--plan-only", help="Write the structured plan without executing it."),
) -> None:
    """Run the validated alignment-to-concordance IQ-TREE 2 route."""

    cfg = _load_config(config_path)
    readiness = assess_readiness(cfg)
    if readiness.status == "not_ready":
        console.print("[red]Not ready; fix readiness issues before execution.[/red]")
        raise typer.Exit(code=2)
    if cfg.input.alignments_dir is None or not cfg.input.alignments_dir.exists():
        console.print("[red]The executable route requires prepared locus alignments.[/red]")
        raise typer.Exit(code=2)

    loci_df = classify_loci_for_selection(compute_locus_metrics(cfg.input.alignments_dir), cfg)
    selected_loci = _selected_locus_paths(cfg, loci_df)
    if not selected_loci:
        console.print("[red]No loci passed selection; execution cannot continue.[/red]")
        raise typer.Exit(code=2)

    stage3 = _stage_dir(cfg, "03_loci")
    stage3.mkdir(parents=True, exist_ok=True)
    loci_df.to_csv(stage3 / "locus_metrics.tsv", sep="\t", index=False)
    loci_df[loci_df["selected"]].to_csv(stage3 / "selected_loci.tsv", sep="\t", index=False)
    loci_df[~loci_df["selected"]].to_csv(stage3 / "excluded_loci.tsv", sep="\t", index=False)

    runs_dir = cfg.project.outdir / "08_runs"
    run_id = build_run_id(cfg, config_path, selected_loci)
    run_dir = runs_dir / run_id
    inputs_dir = run_dir / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    staged_loci_dir = inputs_dir / "loci"
    staged_loci_dir.mkdir(parents=True, exist_ok=True)
    staged_loci: list[Path] = []
    input_manifest_lines = ["order\tsource_path\tstaged_path\tsha256"]
    for index, original in enumerate(selected_loci, start=1):
        staged = staged_loci_dir / f"locus_{index:04d}{original.suffix.lower()}"
        original_hash = sha256_file(original)
        if staged.exists() and sha256_file(staged) != original_hash:
            console.print(f"[red]Staged immutable input changed: {staged}[/red]")
            raise typer.Exit(code=5)
        if not staged.exists():
            shutil.copy2(original, staged)
        staged_loci.append(staged)
        input_manifest_lines.append(
            f"{index}\t{_public_source_label(original, config_path)}\t"
            f"{staged.relative_to(run_dir).as_posix()}\t{original_hash}"
        )
    input_manifest = inputs_dir / "input-manifest.tsv"
    manifest_content = "\n".join(input_manifest_lines) + "\n"
    if input_manifest.exists() and input_manifest.read_text(encoding="utf-8") != manifest_content:
        console.print(f"[red]Immutable input manifest changed: {input_manifest}[/red]")
        raise typer.Exit(code=5)
    input_manifest.write_text(manifest_content, encoding="utf-8")

    concatenated = inputs_dir / "concatenated_alignment.fasta"
    if concatenated.exists():
        expected_concatenated = inputs_dir / ".concatenated_alignment.expected.fasta"
        concatenate_alignments(staged_loci_dir, expected_concatenated, loci_paths=staged_loci)
        if sha256_file(expected_concatenated) != sha256_file(concatenated):
            expected_concatenated.unlink(missing_ok=True)
            console.print(f"[red]Staged immutable concatenated alignment changed: {concatenated}[/red]")
            raise typer.Exit(code=5)
        expected_concatenated.unlink(missing_ok=True)
    else:
        concatenate_alignments(staged_loci_dir, concatenated, loci_paths=staged_loci)

    plan = build_run_plan(
        cfg,
        config_path=config_path,
        run_dir=run_dir,
        concatenated_alignment=concatenated,
        selected_loci=staged_loci,
    )
    plan_path = write_run_plan(plan, run_dir / "run-plan.json")
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "latest-run.json").write_text(
        json.dumps(
            {"run_id": run_id, "run_dir": run_id, "plan_fingerprint": plan.fingerprint},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    console.print(f"Wrote immutable run plan: {plan_path}")
    console.print(f"Plan fingerprint: {plan.fingerprint}")
    console.print(f"Tasks: {len(plan.tasks)} ({len(selected_loci)} selected loci)")
    if plan_only:
        return

    summary = execute_run_plan(plan, cfg)
    console.print(f"Execution status: [bold]{summary.status}[/bold]")
    console.print(summary.message)
    console.print(f"Run state: {summary.state_path}")
    if summary.status == "blocked":
        if summary.reason == "external_tool":
            console.print(
                "Expose a compatible IQ-TREE 2 release (>=2.2.2,<3) on PATH, for example by activating the pinned "
                "Bioconda environment, then rerun the identical command."
            )
            raise typer.Exit(code=3)
        raise typer.Exit(code=4)
    if summary.status == "failed":
        raise typer.Exit(code=5)


@app.command()
def report(config_path: Path) -> None:
    """Generate Markdown + HTML report and provenance artifacts."""
    cfg = _load_config(config_path)
    readiness = assess_readiness(cfg)

    resources: dict | None = None
    if cfg.input.accessions_table is not None and cfg.input.accessions_table.exists():
        try:
            df = load_curated_accessions_table(cfg.input.accessions_table)
            summary = summarize_accessions(df, source_path=cfg.input.accessions_table, outgroup=cfg.input.outgroup)
            resources = {"status": "ok", **summary.__dict__}
            resources["source_path"] = _public_source_label(cfg.input.accessions_table, config_path)
        except (OSError, ValueError) as e:
            resources = {
                "status": "invalid",
                "source_path": _public_source_label(cfg.input.accessions_table, config_path),
                "warnings": [str(e)],
            }
    loci_df: pd.DataFrame | None = None
    if cfg.input.alignments_dir and cfg.input.alignments_dir.exists():
        loci_df = classify_loci_for_selection(compute_locus_metrics(cfg.input.alignments_dir), cfg)
    loci_count = int(len(loci_df)) if loci_df is not None else None
    if loci_df is not None and "selected" in loci_df.columns:
        loci_count = int(loci_df["selected"].sum())
    rec = recommend_route(cfg, loci_count=loci_count)

    commands_candidate = _stage_dir(cfg, "04_route") / "reproducible_commands.sh"
    commands_script: Path | None = commands_candidate if commands_candidate.exists() else None

    prov = build_provenance(config_path=config_path, commands_script=commands_script)
    prov_path = _stage_dir(cfg, "07_fair_package") / "provenance.json"
    write_provenance_json(prov, prov_path)

    # Stage 6: support vs concordance (best-effort summary from detected outputs).
    # Prefer the authoritative structured run when one exists; retain compatibility
    # with the earlier 05_trees command-generation route.
    trees_dir = _stage_dir(cfg, "05_trees")
    latest_run_path = cfg.project.outdir / "08_runs" / "latest-run.json"
    latest_run_dir: Path | None = None
    structured_state_path: Path | None = None
    structured_plan_path: Path | None = None
    if latest_run_path.exists():
        try:
            latest_run = json.loads(latest_run_path.read_text(encoding="utf-8"))
            run_id = latest_run.get("run_id")
            if isinstance(run_id, str) and Path(run_id).name == run_id:
                candidate = latest_run_path.parent / run_id
                if candidate.is_dir():
                    latest_run_dir = candidate
        except (OSError, json.JSONDecodeError):
            latest_run_dir = None
    if latest_run_dir is not None:
        structured_state_path = latest_run_dir / "run-state.json"
        structured_plan_path = latest_run_dir / "run-plan.json"
        structured_reference_dir = latest_run_dir / "outputs" / "reference"
        run_summary = summarize_iqtree_run(structured_reference_dir, "concatenated")
    else:
        run_summary = summarize_iqtree_run(trees_dir, "concatenated")
    iqtree_detected = any([run_summary.iqtree_file, run_summary.treefile, run_summary.contree])

    concordance_requested = bool(cfg.question.needs_concordance or cfg.analysis.require_concordance)
    branch_summary_path = (
        latest_run_dir / "outputs" / "concordance" / "branch-summary.tsv" if latest_run_dir is not None else None
    )
    if concordance_requested:
        concordance_status = (
            "computed"
            if run_summary.concordance_files or (branch_summary_path is not None and branch_summary_path.is_file())
            else "not_computed"
        )
    else:
        concordance_status = "not_requested"

    # If concordance outputs exist, generate a simple flag table.
    cf_flags = _stage_dir(cfg, "06_concordance") / "concordance_flags.tsv"
    cf_interp = interpret_iqtree_concordance(outdir=trees_dir, prefix="concatenated", out_flags_path=cf_flags)
    cf_flags_path = cf_interp.flags_path if cf_interp.status == "computed" else None

    inference: dict[str, object] = {
        "iqtree_detected": iqtree_detected,
        "best_model": run_summary.best_model,
        "log_likelihood": run_summary.log_likelihood,
        "ultrafast_bootstrap_reps": run_summary.ultrafast_bootstrap_reps,
        "treefile": _public_source_label(Path(run_summary.treefile), config_path) if run_summary.treefile else None,
        "contree": _public_source_label(Path(run_summary.contree), config_path) if run_summary.contree else None,
        "concordance_status": concordance_status,
        "concordance_files": run_summary.concordance_files,
        "concordance_table": cf_interp.table_path,
        "concordance_flags": cf_flags_path,
        "gcf_median": cf_interp.gcf_median,
        "scf_median": cf_interp.scf_median,
        "warnings": (
            [
                "Concordance requested but no concordance outputs detected; requires gene trees + an explicit concordance step."
            ]
            if concordance_requested and concordance_status != "computed"
            else []
        ),
    }
    if structured_state_path is not None and structured_state_path.exists():
        structured_state = json.loads(structured_state_path.read_text(encoding="utf-8"))
        task_states = structured_state.get("tasks", {})
        inference.update(
            {
                "execution_status": structured_state.get("status"),
                "run_plan": _public_source_label(structured_plan_path, config_path)
                if structured_plan_path is not None and structured_plan_path.exists()
                else None,
                "run_state": _public_source_label(structured_state_path, config_path),
                "verified_tasks": sum(
                    task.get("status") == "verified" for task in task_states.values() if isinstance(task, dict)
                ),
                "total_tasks": len(task_states),
                "branch_summary": _public_source_label(branch_summary_path, config_path)
                if branch_summary_path is not None and branch_summary_path.exists()
                else None,
            }
        )
        if branch_summary_path is not None and branch_summary_path.exists():
            branch_summary = pd.read_csv(branch_summary_path, sep="\t")
            for column, key in (("gCF", "gcf_median"), ("sCF", "scf_median")):
                if column in branch_summary.columns:
                    values = pd.to_numeric(branch_summary[column], errors="coerce")
                    inference[key] = float(values.median()) if values.notna().any() else None

    md_path = _stage_dir(cfg, "07_fair_package") / "workflow_report.md"
    html_path = _stage_dir(cfg, "07_fair_package") / "workflow_report.html"
    write_markdown_report(
        md_path,
        project_name=cfg.project.name,
        readiness={"status": readiness.status, "issues": readiness.issues, "warnings": readiness.warnings},
        resources=resources,
        route={"route": rec.route.value, "rationale": rec.rationale, "warnings": rec.warnings},
        locus_metrics=loci_df,
        inference=inference,
        commands_script=Path(_public_source_label(commands_script, config_path)) if commands_script else None,
        provenance_path=Path(_public_source_label(prov_path, config_path)),
    )
    write_html_report(
        md_path,
        html_path,
        templates_dir=Path(__file__).parent / "templates",
        context={"project_name": cfg.project.name, "generated_at": datetime.now().isoformat()},
    )
    console.print(f"Wrote report: {html_path}")


@app.command(name="package")
def package_cmd(config_path: Path) -> None:
    """Collect key artifacts into a FAIR package with checksums and metadata."""
    cfg = _load_config(config_path)
    report_md = _stage_dir(cfg, "07_fair_package") / "workflow_report.md"
    report_html = _stage_dir(cfg, "07_fair_package") / "workflow_report.html"
    prov = _stage_dir(cfg, "07_fair_package") / "provenance.json"
    cmd = _stage_dir(cfg, "04_route") / "reproducible_commands.sh"
    missing = [path for path in (report_md, report_html, prov) if not path.is_file()]
    if missing:
        console.print("[red]Package prerequisites are missing. Run the report command first.[/red]")
        for path in missing:
            console.print(f"[red]- {path}[/red]")
        raise typer.Exit(code=2)

    extra: list[Path] = []
    stage2 = _stage_dir(cfg, "02_resources")
    if stage2.exists():
        extra.append(stage2)
    stage3 = _stage_dir(cfg, "03_loci")
    if stage3.exists():
        extra.append(stage3)
    stage5 = _stage_dir(cfg, "05_trees")
    if stage5.exists():
        extra.append(stage5)
    stage6 = _stage_dir(cfg, "06_concordance")
    if stage6.exists():
        extra.append(stage6)
    stage8 = cfg.project.outdir / "08_runs"
    if stage8.exists():
        extra.append(stage8)

    config_snapshot = cfg.model_dump(mode="json")
    config_snapshot["project"]["outdir"] = _public_source_label(cfg.project.outdir, config_path)
    for field in ("alignments_dir", "gene_trees_dir", "taxa_table", "accessions_table"):
        value = getattr(cfg.input, field)
        if value is not None:
            config_snapshot["input"][field] = _public_source_label(value, config_path)
    config_snapshot["_source"] = {"file": config_path.name, "sha256": sha256_file(config_path)}
    snapshot_path = _stage_dir(cfg, "07_fair_package") / "project.snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(config_snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    extra.append(snapshot_path)

    pkg = package_fair_outputs(
        outdir=cfg.project.outdir,
        report_md=report_md,
        report_html=report_html,
        provenance_json=prov,
        commands_script=cmd if cmd.exists() else None,
        extra_paths=extra,
    )
    console.print(f"Packaged outputs: {pkg}")


@app.command(name="verify-package")
def verify_package_cmd(package_dir: Path) -> None:
    """Verify checksums, inventory completeness, and core RO-Crate metadata."""

    errors = verify_fair_package(package_dir)
    if errors:
        console.print(f"[red]Package verification failed with {len(errors)} error(s):[/red]")
        for error in errors:
            console.print(f"[red]- {error}[/red]")
        raise typer.Exit(code=5)
    console.print(f"[green]Package verified:[/green] {package_dir}")


if __name__ == "__main__":
    app()
