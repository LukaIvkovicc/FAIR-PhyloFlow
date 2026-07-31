# Current Status

FAIR PhyloFlow is a route-aware phylogenomics workflow. It turns curated
inputs, locus diagnostics, tool commands, tree outputs,
support/concordance summaries, reports, and provenance into an auditable
analysis workflow.

## Design Premise

The current prototype demonstrates a central workflow premise:

- phylogenomics is not only running a tree tool;
- data readiness and locus inclusion are methodological decisions;
- route choice should depend on the biological question;
- support and concordance need to be separated;
- every decision, command, and reusable output should be traceable.

## What Works Now

- `project.yaml` validation and config-relative paths.
- Curated accession table normalization and registry output.
- Taxon/outgroup/accession readiness warnings.
- Per-locus FASTA metrics.
- Selected/excluded locus tables with explicit reasons.
- Selected-locus-only concatenation and command staging.
- Route recommendation from question type, domain profile, and data state.
- Route-aware tool adapters for IQ-TREE, RAxML-NG, ParGenes, ASTRAL, BUSCO,
  and BUCKy.
- Reproducible command generation.
- Optional IQ-TREE execution when installed.
- Basic IQ-TREE and concordance-output parsing when outputs exist.
- Content-addressed structured execution plans with staged, checksummed inputs.
- Exclusive run locking and checksum-aware recursive invalidation.
- Validated reference-tree, per-locus-tree, gCF, sCF, and normalized
  branch-summary tasks for compatible IQ-TREE 2 installations.
- Markdown/HTML report generation.
- Provenance JSON and reusable output package with SHA-256 and RO-Crate
  metadata.
- Portable configuration snapshots and `verify-package` integrity validation.
- Test suite covering the core decision/execution consistency.

## What To Run First

Run:

```bash
python -m pytest -q
fair-phyloflow check examples/penicillium_camemberti_case/project.yaml
fair-phyloflow plan examples/penicillium_camemberti_case/project.yaml
fair-phyloflow run examples/penicillium_camemberti_case/project.yaml --no-execute
fair-phyloflow report examples/penicillium_camemberti_case/project.yaml
fair-phyloflow package examples/penicillium_camemberti_case/project.yaml
fair-phyloflow verify-package \
  results/penicillium_camemberti_case/07_fair_package
```

Then inspect:

```
results/penicillium_camemberti_case/
|-- 02_resources/accessions_normalized.tsv
|-- 03_loci/selected_loci.tsv
|-- 03_loci/excluded_loci.tsv
|-- 04_route/recommended_route.txt
|-- 04_route/reproducible_commands.sh
|-- 05_trees/concatenated_alignment.fasta
|-- 05_trees/selected_loci_alignments/
`-- 07_fair_package/
    |-- report.md
    |-- report.html
    |-- project.snapshot.json
    |-- provenance.json
    |-- manifest-sha256.tsv
    `-- ro-crate-metadata.json
```

The important demonstration point is that excluded loci remain documented but
do not enter concatenation or per-locus command inputs.

## Source Map

- `src/fair_phyloflow/config.py`: loads workflow configuration and resolves
  paths relative to `project.yaml`.
- `src/fair_phyloflow/cli.py`: defines the user-facing CLI commands:
  `check`, `status`, `plan`, `run`, `execute`, `report`, `package`, and
  `verify-package`.
- `src/fair_phyloflow/readiness.py`: checks files, taxa, accessions, and
  outgroup consistency.
- `src/fair_phyloflow/resources.py`: normalizes curated accession metadata.
- `src/fair_phyloflow/loci.py`: computes locus metrics and selected/excluded
  decisions.
- `src/fair_phyloflow/concatenate.py`: builds selected-locus-only concatenated
  alignments with validation.
- `src/fair_phyloflow/routes.py`: recommends analytical routes.
- `src/fair_phyloflow/adapters/`: tool adapter contracts and command planners.
- `src/fair_phyloflow/commands.py`: writes reproducible command scripts.
- `src/fair_phyloflow/execution.py`: detects external tools, captures version
  banners, and runs shell commands safely.
- `src/fair_phyloflow/status.py`: summarizes adapter/tool availability for a
  project.
- `src/fair_phyloflow/iqtree_results.py` and `concordance.py`: parse detected
  result/concordance outputs.
- `src/fair_phyloflow/reporting.py` and `templates/report.html.j2`: generate
  Markdown/HTML reports.
- `src/fair_phyloflow/provenance.py`: writes machine-readable provenance.
- `src/fair_phyloflow/packaging.py`: collects reusable FAIR-oriented outputs.

## Repository Tour

- `README.md`: main entry point, quickstart, demo commands, output map, and
  high-level explanation.
- `pyproject.toml`: Python package metadata, dependencies, CLI entry point, and
  test configuration.
- `src/fair_phyloflow/`: reusable backend package. This is the real workflow
  engine used by the CLI and future UI.
- `src/fair_phyloflow/adapters/`: modular tool layer for IQ-TREE, RAxML-NG,
  ParGenes, ASTRAL, BUSCO, and BUCKy.
- `src/fair_phyloflow/templates/`: report templates, currently including the
  HTML workflow report.
- `app/streamlit_app.py`: early UI/workbench entry point. The CLI/backend is
  the authoritative layer; the UI should sit on top of it.
- `examples/demo_project/`: small toy alignment demo for basic workflow checks.
- `examples/curated_accessions_project/`: accession-only demo showing resource
  registration without alignments.
- `examples/penicillium_camemberti_case/`: main phylogenomics validation
  scaffold with candidate accessions and synthetic control alignments; neither
  is presented as validated biological evidence.
- `tests/`: regression tests for config loading, readiness, resources, loci,
  concatenation, adapters, provenance, routes, and tool status.
- `docs/WORKFLOW_SPEC.md`: formal workflow contract.
- `docs/ARCHITECTURE.md`: implementation and ETL architecture.
- `docs/VALIDATION_GUIDE.md`: validation and adoption checks.
- `docs/ROADMAP.md`: completed execution milestone and later workflow layers.
- `docs/ANALYSIS_CAPABILITIES.md`: supported route types and analysis
  boundaries.
- `docs/DATA_SUPPORT.md`: current and planned data layers.
- `docs/TOOL_ADAPTERS.md`: adapter support levels and extension contract.
- `docs/PENICILLIUM_CASE_STUDY.md`: validation story for the Penicillium
  example.
- `docs/ROUTE_MATRIX.md`: route families and support-level overview.
- `results/`: generated outputs from demo runs; they are reproducible from
  `examples/*/project.yaml` and are not repository source.
- `Dockerfile` and `docker-compose.yml`: early containerization/dev-environment
  support.

## What It Is Not Yet

This is not yet a full raw-data-to-publication workflow. It does not yet
automate genome download, raw read processing, ortholog inference, BUSCO
execution/parsing, ASTRAL execution/parsing, or biological species delimitation
decisions.

Those are future workflow layers. The current milestone is a transparent,
testable workflow engine with one complete prepared-alignment execution route.

## Next Move

Verify the executable route against the pinned real IQ-TREE 2 environment in
GitHub Actions, then validate it with genuine curated biological inputs when
those data are ready. Biological validation remains distinct from the
synthetic software-contract fixtures.
