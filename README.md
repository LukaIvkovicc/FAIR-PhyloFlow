# FAIR PhyloFlow

> Decision-aware, reproducible phylogenomics with transparent provenance.

[![Python 3.11–3.14](https://img.shields.io/badge/python-3.11--3.14-3776AB.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](docs/ROADMAP.md)
[![CI](https://github.com/LukaIvkovicc/FAIR-PhyloFlow/actions/workflows/ci.yml/badge.svg)](https://github.com/LukaIvkovicc/FAIR-PhyloFlow/actions/workflows/ci.yml)

FAIR PhyloFlow is a configuration-driven workflow for turning curated
phylogenomics inputs into explicit decisions, validated executions, traceable
evidence, and FAIR packages.

It is designed around a simple premise: phylogenomics is not just "run a tree
tool." Users must decide which data are suitable, which route fits the
biological question, which loci are usable, how support and concordance should
be interpreted, and how the whole analysis can be documented for reuse.

## Architecture At A Glance

Workflow and evidence layer:

- strict, portable project configuration
- immutable execution plans and task state
- checksum-aware invalidation, locking, and safe resumption
- provenance, reporting, FAIR packaging, RO-Crate metadata, and verification
- explicit tool capabilities and support levels

Phylogenomics layer:

- accession/taxon readiness
- locus validation and selection
- phylogenomic route recommendation
- IQ-TREE 2 execution and concordance parsing
- RAxML-NG, ParGenes, ASTRAL, BUSCO, and BUCKy integration levels

## What It Does Now

FAIR PhyloFlow currently supports:

```text
project.yaml
    |
    v
check   -> validate config and readiness
status  -> inspect route-aware tool adapters and support levels
plan    -> normalize resources, score loci, recommend route
run     -> concatenate alignments, generate commands, optionally execute tools
execute -> run the validated, resumable IQ-TREE 2 alignment-to-concordance route
report  -> summarize decisions, support/concordance state, provenance
package -> collect reusable FAIR outputs
```

Operational features:

- validates `project.yaml`
- registers and normalizes curated accession tables
- checks basic readiness
- computes locus metrics from per-locus FASTA alignments
- writes selected/excluded locus tables with explicit reasons
- recommends analytical routes from the biological question
- maps routes to tool adapters and support levels
- generates reproducible commands
- optionally runs IQ-TREE when available
- parses basic IQ-TREE/concordance outputs when present
- writes Markdown/HTML reports
- writes machine-readable provenance
- packages outputs with checksums and FAIR-oriented metadata

## What It Does Not Do Yet

The prototype does **not** yet fully automate:

- genome download from accessions
- raw read QC, assembly, or annotation
- ortholog inference from genomes/proteomes
- BUSCO execution/parsing
- large-scale ParGenes execution
- ASTRAL execution/parsing
- full introgression/reticulation analysis
- automatic biological species delimitation decisions

These are planned workflow layers, not hidden promises.

## Supported Analysis Routes

| Route | Current support | Typical use |
| --- | --- | --- |
| Concatenation-based ML tree | validated IQ-TREE 2 execution and parsing; RAxML-NG commands | first-pass relationship inference |
| Gene-tree / concordance-aware route | locked/resumable per-locus IQ-TREE 2, gCF/sCF, branch evidence | species delimitation, conflict-sensitive analysis |
| Species-tree route | ASTRAL guidance with an illustrative command scaffold | gene-tree/species-tree comparison |
| Conflict / reticulation route | guidance and warnings | advanced introgression, hybridization, HGT, recombination questions |

See [docs/ANALYSIS_CAPABILITIES.md](docs/ANALYSIS_CAPABILITIES.md).

## Data Layers

FAIR PhyloFlow distinguishes how a user enters the workflow from what
phylogenomics data layer they provide.

| Data type | Current support |
| --- | --- |
| `accessions` | normalize/register/report |
| `locus_alignments` | nucleotide FASTA metrics, selection, concatenation, commands |
| `gene_trees` | route shortcut; concordance/species-tree layer planned |
| `genome_assemblies` | planned |
| `proteomes` | planned |
| `orthogroups` | planned |
| `snp_matrix` | guidance/future |
| `raw_reads` | future extension |

See [docs/DATA_SUPPORT.md](docs/DATA_SUPPORT.md).

## Quickstart

FAIR PhyloFlow is tested on Python 3.11 through 3.14. External phylogenomic
programs are optional for planning and report generation; use
`fair-phyloflow status` to see which tools are available.

Clone the repository first:

```bash
git clone https://github.com/LukaIvkovicc/FAIR-PhyloFlow.git
cd FAIR-PhyloFlow
```

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
fair-phyloflow --version
```

### WSL / Linux

For phylogenomics tools, WSL/Linux is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
fair-phyloflow --version
```

For development, install the development and UI extras and run the complete
local gate:

```bash
python -m pip install -e ".[dev,ui]"
make check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution requirements.

### Reproducible IQ-TREE Environment

The checked-in environment pins IQ-TREE 2 for the executable integration
route. From the repository root, create and activate it with either Conda or
Micromamba:

```bash
conda env create -f environment.yml
conda activate fair-phyloflow
fair-phyloflow status examples/demo_project/project.yaml
```

The Micromamba equivalent is:

```bash
micromamba create -f environment.yml
micromamba activate fair-phyloflow
fair-phyloflow status examples/demo_project/project.yaml
```

An activated Conda/Micromamba environment exposes `iqtree2` on `PATH`; keep
`execution.mode: local` in `project.yaml`. Version 0.1.0 validates and invokes
that executable directly but does not create or launch environment runtimes.

### Container

The container provides the Streamlit launcher and runs as an unprivileged user:

```bash
docker compose up --build
```

Then open `http://localhost:8501`. The image does not include IQ-TREE; the
interface generates commands and reports without executing external
phylogenomic tools. Generated results are retained in the Compose-managed
volume.

## Run The Demo

Toy alignment demo:

```bash
fair-phyloflow check examples/demo_project/project.yaml
fair-phyloflow status examples/demo_project/project.yaml
fair-phyloflow plan examples/demo_project/project.yaml
fair-phyloflow run examples/demo_project/project.yaml --no-execute
fair-phyloflow report examples/demo_project/project.yaml
fair-phyloflow package examples/demo_project/project.yaml
fair-phyloflow verify-package results/demo_project/07_fair_package
```

Preview the structured executable-route plan without running external tools:

```bash
fair-phyloflow execute examples/demo_project/project.yaml --plan-only
```

With a compatible IQ-TREE 2 executable (`>=2.2.2,<3`) available, execute the
validated and resumable route:

```bash
fair-phyloflow execute examples/demo_project/project.yaml
fair-phyloflow report examples/demo_project/project.yaml
fair-phyloflow package examples/demo_project/project.yaml
```

Every external task is represented by an argument array, fingerprinted,
validated after execution, and recorded under `08_runs/<run-id>/run-state.json`.
Selected alignments are staged inside the run with an input manifest. Verified
tasks are skipped only when their fingerprints, formats, and recorded checksums
still match; changed evidence recursively invalidates dependent results.
Every generated FAIR package can be independently checked with
`fair-phyloflow verify-package <package-directory>`.

Curated-accessions demo:

```bash
fair-phyloflow check examples/curated_accessions_project/project.yaml
fair-phyloflow status examples/curated_accessions_project/project.yaml
fair-phyloflow plan examples/curated_accessions_project/project.yaml
fair-phyloflow report examples/curated_accessions_project/project.yaml
```

Penicillium camemberti validation scaffold:

```bash
fair-phyloflow check examples/penicillium_camemberti_case/project.yaml
fair-phyloflow status examples/penicillium_camemberti_case/project.yaml
fair-phyloflow plan examples/penicillium_camemberti_case/project.yaml
fair-phyloflow run examples/penicillium_camemberti_case/project.yaml --no-execute
fair-phyloflow report examples/penicillium_camemberti_case/project.yaml
fair-phyloflow package examples/penicillium_camemberti_case/project.yaml
```

The Penicillium example currently combines candidate public accession metadata
with synthetic control alignments. The accessions require independent source
validation, and the alignments are test fixtures rather than biological
evidence. Replace them with verified metadata and real single-copy ortholog
alignments before drawing biological conclusions.

## Outputs To Inspect

```text
results/
|-- demo_project/
|-- curated_accessions_project/
`-- penicillium_camemberti_case/
    |-- 02_resources/      normalized accession registry
    |-- 03_loci/           locus metrics and selected/excluded loci
    |-- 04_route/          route recommendation and command script
    |-- 05_trees/          selected alignment copies and generated tree outputs
    |-- 06_concordance/    concordance flags when available
    |-- 07_fair_package/   report, provenance, checksums, RO-Crate metadata
    `-- 08_runs/           immutable plans, inputs, state, logs, and outputs
```

Relative paths in `project.yaml` are resolved from that config file's folder.
Tree inputs are generated from selected loci only; excluded loci remain reported
but are not concatenated or staged for per-locus inference commands.

## Tool Adapters

Current adapters:

- IQ-TREE 2
- RAxML-NG
- ParGenes
- ASTRAL
- BUSCO
- BUCKy

Run:

```bash
fair-phyloflow status examples/penicillium_camemberti_case/project.yaml
```

See [docs/TOOL_ADAPTERS.md](docs/TOOL_ADAPTERS.md).

## Documentation Map

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): backend and ETL contract
- [docs/ANALYSIS_CAPABILITIES.md](docs/ANALYSIS_CAPABILITIES.md): supported analyses
- [docs/DATA_SUPPORT.md](docs/DATA_SUPPORT.md): supported and planned data layers
- [docs/TOOL_ADAPTERS.md](docs/TOOL_ADAPTERS.md): tool adapter contracts
- [docs/PENICILLIUM_CASE_STUDY.md](docs/PENICILLIUM_CASE_STUDY.md): validation scaffold
- [docs/VALIDATION_GUIDE.md](docs/VALIDATION_GUIDE.md): workflow validation and adoption checks
- [docs/ROADMAP.md](docs/ROADMAP.md): implementation and scientific-validation roadmap
- [docs/WORKFLOW_SPEC.md](docs/WORKFLOW_SPEC.md): workflow contract
- [docs/ROUTE_MATRIX.md](docs/ROUTE_MATRIX.md): route families and support levels
- [docs/EXECUTABLE_ROUTE.md](docs/EXECUTABLE_ROUTE.md): executable route and evidence contract
- [docs/current_status.md](docs/current_status.md): concise implementation status and source map

## Why This Is Not Just An IQ-TREE Wrapper

IQ-TREE is one executable adapter in FAIR PhyloFlow. The project contribution
is the decision-and-evidence lifecycle around phylogenomics tools: structured
inputs, readiness, explicit decisions, validated execution, provenance, and
reusable reporting.

The workflow is intentionally modular so tools can evolve without replacing the
decision framework.

## Citation And Reuse

FAIR PhyloFlow is released under the [MIT License](LICENSE). If you use or
evaluate it in research, cite the metadata in
[CITATION.cff](CITATION.cff). Please note that the repository is currently an
alpha research prototype; see the capability and roadmap documents before
relying on it for production analyses.

## Contributing

Bug reports, scientific-method questions, documentation improvements, and code
contributions are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md), and
use [SECURITY.md](SECURITY.md) for private vulnerability reporting.
