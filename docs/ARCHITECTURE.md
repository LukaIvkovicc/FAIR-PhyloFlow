# Architecture And ETL

FAIR PhyloFlow separates phylogenomics decisions from the reusable workflow
mechanics that protect scientific evidence. The workflow layer provides
configuration, execution state, integrity, provenance, reporting, packaging,
and verification. The phylogenomics layer provides scientific inputs,
readiness rules, route decisions, tool adapters, validators, and
interpretation.

## Layer Boundaries

```text
FAIR PhyloFlow workflow and evidence layer
|-- immutable plans and task state
|-- locks, checksums, invalidation, and resumption
|-- provenance and portable evidence records
|-- reports, FAIR package assembly, RO-Crate, verification
`-- tool-adapter contracts
    |
    `-- phylogenomics logic
        |-- biological question and input schema
        |-- accession, taxon, alignment, and locus checks
        |-- route recommendation
        |-- IQ-TREE execution/concordance validation
        `-- alternative phylogenomics tool adapters
```

This is an internal modularity boundary, not a cross-domain plugin claim.
FAIR PhyloFlow is intentionally a phylogenomics project. The `domain_pack`
configuration field and internal protocol preserve an explicit schema identity
for reproducibility and future versioning.

## Current Command Flow

```text
project.yaml
    |
    v
check   -> validate config and readiness
status  -> inspect route-aware tool adapters and support levels
plan    -> normalize resources, score loci, recommend route
run     -> concatenate alignments, generate commands, optionally execute tools
execute -> stage immutable inputs and run the validated IQ-TREE 2 concordance route
report  -> summarize decisions, support/concordance state, provenance
package -> collect reusable FAIR outputs
verify-package -> validate package inventory, checksums, and RO-Crate structure
```

`package` is downstream of `report`: it expects the report and provenance files
to exist before collecting them into the reusable package.

## ETL Model

### Extract

The workflow extracts structured information from user-provided, curated inputs:

- `project.yaml`: project metadata, explicit workflow schema, biological
  question, domain profile, input mode, route preferences, execution settings,
  and FAIR settings.
- `accessions.tsv`: curated accessions, taxa, strains, sources, and optional
  inclusion/exclusion metadata.
- `taxa.tsv`: taxon sampling context and outgroup information.
- `alignments/`: per-locus FASTA alignments.
- Existing outputs: IQ-TREE tree files, concordance tables, logs, and command
  scripts when present.

### Transform

The workflow converts those inputs into explicit, auditable decisions:

- Validate required config fields and input-mode-specific paths.
- Resolve relative project/input paths from the `project.yaml` location, so
  examples and case folders are portable across working directories.
- Normalize accession/taxon columns and preserve source metadata.
- Assess readiness: missing files, missing outgroup, parseability, minimal taxon
  sampling, accession table validity, and taxa/accession/outgroup consistency.
- Calculate locus metrics: number of taxa, alignment length, and missingness.
- Classify loci into selected/excluded sets with explicit exclusion reasons.
- Use selected loci, not every FASTA in the source folder, for generated tree
  inputs and per-locus command scaffolds.
- Recommend a route based on biological question, domain profile, input mode,
  concordance requirements, and locus count.
- Map the recommended route to tool adapters and support levels.
- Generate reproducible commands for route-compatible tools.
- Parse available inference/concordance outputs when present.

### Load

The workflow loads each decision and output into a predictable project
directory. Entries marked "when present" depend on the input mode and commands
that have run:

```text
results/<project>/
|-- 02_resources/                         when accession metadata is available
|   |-- accessions_normalized.tsv
|   `-- resource_registry.json
|-- 03_loci/                              when alignments have been planned
|   |-- locus_metrics.tsv
|   |-- selected_loci.tsv
|   `-- excluded_loci.tsv
|-- 04_route/
|   |-- recommended_route.txt
|   `-- reproducible_commands.sh
|-- 05_trees/                             when alignments have been planned
|   |-- selected_loci_alignments/
|   `-- concatenated_alignment.fasta
|-- 06_concordance/                       when concordance output is available
|   `-- concordance_flags.tsv
|-- 07_fair_package/                      final package after `package`
|   |-- report.md
|   |-- report.html
|   |-- provenance.json
|   |-- project.snapshot.json
|   |-- reproducible_commands.sh          when generated
|   |-- 02_resources/                     when generated
|   |-- 03_loci/                          when generated
|   |-- 05_trees/                         when generated
|   |-- 06_concordance/                   when generated
|   |-- 08_runs/                          latest structured run only, when present
|   |-- manifest-sha256.tsv
|   `-- ro-crate-metadata.json
`-- 08_runs/                              live immutable execution records
    |-- latest-run.json
    `-- <run-id>/
        |-- inputs/
        |-- logs/
        |-- outputs/
        |-- run-plan.json
        `-- run-state.json
```

Before `package` runs, the reporting command stages
`workflow_report.md`, `workflow_report.html`, and `provenance.json` under
`07_fair_package/`. Packaging atomically replaces that staging directory with
the final package shown above, renaming the reports to `report.md` and
`report.html`. The live top-level `08_runs/` tree remains separate; only the
run selected by `latest-run.json` is copied into a package.

## Support Levels

Tool support is explicit. This keeps the prototype honest and prevents the
workflow from pretending that every route is fully automated.

- `guided`: the workflow explains the route and requirements.
- `command`: the workflow writes reproducible commands/templates.
- `executable`: the workflow can run the tool directly.
- `parsed`: the workflow can parse and interpret outputs.

Current adapters include IQ-TREE 2, RAxML-NG, ParGenes, ASTRAL, BUSCO, and
BUCKy. IQ-TREE is the first parsed/executable target; the others are currently
command-generation or guidance scaffolds.

## Current Automation Boundary

Already operational:

- YAML-driven project configuration
- readiness checks
- curated accession normalization
- locus metrics and selection/exclusion tables
- biological-question-based route recommendation
- route-aware command generation
- optional IQ-TREE execution when installed
- best-effort IQ-TREE/concordance parsing
- content-addressed, locked, resumable IQ-TREE 2 route execution
- staged input manifests and checksum-aware evidence validation
- reference-tree, per-locus-tree, gCF, sCF, and branch-summary validation
- Markdown/HTML report generation
- provenance JSON
- reusable FAIR package with a checksum-verified inventory
- local package integrity verification

Not yet fully automated:

- downloading genomes from accessions
- assembly/annotation from raw reads
- ortholog inference from genomes/proteomes
- BUSCO execution and parsing
- large-scale ParGenes execution
- ASTRAL species-tree execution/parsing
- full reticulation/introgression analysis
- biological species-delimitation decisions

Those are future adapters or workflow extensions, not hidden promises.

See [DATA_SUPPORT.md](DATA_SUPPORT.md) for the current and planned data layers.

## Design Principles

- The contribution is workflow design and decision logic, not a new scientific
  algorithm.
- FAIRness is embedded during the workflow, not added only after analysis.
- Domain decisions are explicit, justified, and testable.
- Scientific tools remain adapters rather than becoming the project identity.
- Phylogenomics decisions stay separate from generic execution and evidence
  mechanics.
- Evidence integrity and verification apply consistently across supported
  phylogenomics routes.
