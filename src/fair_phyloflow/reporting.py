from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import PRODUCT_NAME


def _dataframe_to_markdown(df: pd.DataFrame) -> str:
    columns = [str(c) for c in df.columns]
    rows = [[str(value) for value in row] for row in df.itertuples(index=False, name=None)]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _markdown_subset_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    html: list[str] = []
    in_ul = False
    in_table = False
    in_section = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            html.append("</ul>")
            in_ul = False

    def close_table() -> None:
        nonlocal in_table
        if in_table:
            html.append("</tbody></table>")
            in_table = False

    def close_section() -> None:
        nonlocal in_section
        close_ul()
        close_table()
        if in_section:
            html.append("</section>")
            in_section = False

    for line in lines:
        if not line.strip():
            close_ul()
            close_table()
            continue
        if line.startswith("# "):
            close_section()
            html.append(f"<h1>{escape(line[2:])}</h1>")
            continue
        if line.startswith("## "):
            close_section()
            html.append(f"<section><h2>{escape(line[3:])}</h2>")
            in_section = True
            continue
        if line.startswith("| "):
            close_ul()
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= {"-"} for c in cells):
                continue
            if not in_table:
                html.append("<table><thead><tr>")
                html.extend(f"<th>{escape(c)}</th>" for c in cells)
                html.append("</tr></thead><tbody>")
                in_table = True
            else:
                html.append("<tr>")
                html.extend(f"<td>{escape(c)}</td>" for c in cells)
                html.append("</tr>")
            continue
        close_table()
        if line.startswith("- "):
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            item = escape(line[2:]).replace("**", "")
            html.append(f"<li>{item}</li>")
            continue
        close_ul()
        html.append(f"<p>{escape(line)}</p>")

    close_ul()
    close_table()
    close_section()
    return "\n".join(html)


def write_markdown_report(
    out_path: Path,
    *,
    project_name: str,
    readiness: dict,
    resources: dict | None,
    route: dict,
    locus_metrics: pd.DataFrame | None,
    inference: dict | None,
    commands_script: Path | None,
    provenance_path: Path | None,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# {PRODUCT_NAME} report: {project_name}\n")

    lines.append("## Readiness")
    lines.append(f"- Status: **{readiness['status']}**")
    for i in readiness.get("issues", []):
        lines.append(f"- Issue: {i}")
    for w in readiness.get("warnings", []):
        lines.append(f"- Warning: {w}")
    lines.append("")

    lines.append("## Route recommendation")
    lines.append(f"- Route: **{route['route']}**")
    for r in route.get("rationale", []):
        lines.append(f"- Rationale: {r}")
    for w in route.get("warnings", []):
        lines.append(f"- Warning: {w}")
    lines.append("")

    if resources is not None:
        lines.append("## Curated resources")
        if resources.get("status"):
            lines.append(f"- Status: **{resources['status']}**")
        for k in ["source_path", "n_records", "n_unique_taxa", "outgroup"]:
            if k in resources and resources[k] is not None:
                lines.append(f"- {k}: {resources[k]}")
        cols = resources.get("columns")
        if isinstance(cols, list) and cols:
            lines.append(f"- columns: {', '.join(str(c) for c in cols)}")
        for w in resources.get("warnings", []) or []:
            lines.append(f"- Warning: {w}")
        lines.append("")

    if locus_metrics is not None and not locus_metrics.empty:
        lm = locus_metrics
        lines.append("## Locus metrics (summary)")
        lines.append(f"- Loci counted: {len(lm)}")
        if "selected" in lm.columns:
            lines.append(f"- Loci selected: {int(lm['selected'].sum())}")
            lines.append(f"- Loci excluded: {int((~lm['selected']).sum())}")
        lines.append(f"- Median alignment length: {int(lm['alignment_length'].median())}")
        lines.append(f"- Median taxa per locus: {int(lm['n_taxa'].median())}")
        lines.append(f"- Median mean-missing fraction: {float(lm['mean_missing_fraction'].median()):.3f}")
        lines.append("")

        lines.append("## Locus metrics (table)")
        lines.append(_dataframe_to_markdown(lm))
        lines.append("")

    if inference is not None:
        lines.append("## Inference outputs (support / concordance)")
        if inference.get("iqtree_detected") is not None:
            lines.append(f"- IQ-TREE outputs detected: **{inference['iqtree_detected']}**")
        for k in ["best_model", "log_likelihood", "ultrafast_bootstrap_reps", "treefile", "contree"]:
            if k in inference and inference[k] is not None:
                lines.append(f"- {k}: {inference[k]}")
        for k in [
            "execution_status",
            "verified_tasks",
            "total_tasks",
            "run_plan",
            "run_state",
            "branch_summary",
            "concordance_table",
            "concordance_flags",
            "gcf_median",
            "scf_median",
        ]:
            if k in inference and inference[k] is not None:
                lines.append(f"- {k}: {inference[k]}")
        if "concordance_status" in inference:
            lines.append(f"- concordance_status: {inference['concordance_status']}")
        cfiles = inference.get("concordance_files")
        if isinstance(cfiles, list) and cfiles:
            lines.append(f"- concordance_files: {', '.join(cfiles)}")
        for w in inference.get("warnings", []) or []:
            lines.append(f"- Warning: {w}")
        lines.append("")

    if commands_script is not None:
        lines.append("## Reproducible commands")
        lines.append(f"- Script: {commands_script}")
        lines.append("")

    if provenance_path is not None:
        lines.append("## Provenance")
        lines.append(f"- provenance.json: {provenance_path}")
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def write_html_report(markdown_path: Path, html_path: Path, *, templates_dir: Path, context: dict) -> Path:
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=select_autoescape(["html"]))
    tpl = env.get_template("report.html.j2")
    md = markdown_path.read_text(encoding="utf-8")
    html = tpl.render(markdown=md, report_html=_markdown_subset_to_html(md), **context)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    return html_path
