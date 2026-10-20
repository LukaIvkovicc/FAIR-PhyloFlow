# FAIR PhyloFlow overview

Version 2 is the selected main README and project overview.
[Compare it with the compact Version 1](COMPARISON.md).
The `-v1` files retain the compact design with source-audit clarifications;
the original unversioned files remain preserved. The `-v2`
SVG is the canonical source for the active figure and its PNG/PDF exports.

The repository overview is available as an editable [SVG](fair-phyloflow-overview-v2.svg),
a [PNG](fair-phyloflow-overview-v2.png), and a [vector PDF](fair-phyloflow-overview-v2.pdf).
The SVG is the canonical source; update the exports whenever it changes.
It uses selectable text, no external assets, and an accessible title and description.

## Figure caption

**FAIR PhyloFlow links scientific decisions to reusable phylogenomic evidence.**
A biological question, configuration, and curated inputs establish the analysis
context. Readiness checks and locus diagnostics produce explicit inclusion and
exclusion decisions. Route recommendation records rationale, warnings, and tool
support. The implemented IQ-TREE 2 route uses selected nucleotide alignments to
infer a concatenated reference tree and per-locus gene trees. Gene concordance
(gCF) uses the reference tree and verified gene-tree set; site concordance (sCF)
uses the reference tree and concatenated alignment. Concordance values are
normalized by branch ID, while traditional branch support remains a separate
evidence type. Reports and FAIR-oriented packages retain decisions, provenance,
and available outputs. Immutable execution plans, staged inputs, checksums,
locking, and dependency-aware resumption protect execution evidence. The dashed
panel distinguishes command/guidance support and future automation from the
implemented route. Package verification checks local integrity; publication,
repository deposition, and biological validation are separate activities.

## Reading the figure

- The numbered stages show the conceptual lifecycle, not a literal shell-command sequence.
  Planning and reporting are available without executing external tools. An
  accession-only project can register resources without entering tree inference.
  Reporting can summarize existing results without performing new inference.
- Route families are concatenation, gene-tree/concordance, species-tree, and
  conflict/reticulation. Recommendation considers the question, profile, input
  mode, configuration preferences, and locus count; it also supports overrides.
  Recommendation does not imply that every route can execute. The researcher
  invokes `execute` explicitly; it runs the fixed IQ-TREE alignment-to-concordance
  plan rather than dispatching the recommended route automatically.
- The inset expands the authoritative `execute` route. Its upper path separates
  concatenation from reference-tree inference; its lower node compresses
  per-locus inference and verified gene-tree collection. It is a conceptual
  dependency diagram, not a one-box-per-task execution graph.
- The researcher uses already curated data, defines the question, and configures
  the study. PhyloFlow applies
  checks and thresholds, orchestrates execution, validates artifacts, and packages
  evidence. IQ-TREE performs tree inference and concordance calculations.
  Readiness checks do not establish orthology or full biological suitability.
- Excluded loci remain in decision tables and reports but do not enter tree
  inputs. Biological interpretation and species-delimitation judgments remain
  with the researcher.
- `run` provides command generation and optional execution; `execute` provides
  the structured, validated, resumable IQ-TREE route. Run `report` before
  `package`, then `verify-package` on the resulting package directory.
- FAIR means Findable, Accessible, Interoperable, and Reusable. The figure shows
  implemented mechanisms supporting those goals, not a claim of FAIR certification
  or automatic public deposition. Packaged run records are portable evidence
  snapshots, not directly resumable execution plans.
- Current example alignments are synthetic fixtures. Software-contract validation
  should not be presented as validation of a biological conclusion.

## Implementation references

| Figure claim | Source of truth |
| --- | --- |
| Configuration and readiness | [config.py](../../src/fair_phyloflow/config.py), [readiness.py](../../src/fair_phyloflow/readiness.py) |
| Accession registration | [resources.py](../../src/fair_phyloflow/resources.py) |
| Locus metrics and explicit exclusion reasons | [loci.py](../../src/fair_phyloflow/loci.py) |
| Route rationale, warnings, and overrides | [routes.py](../../src/fair_phyloflow/routes.py) |
| Selected-locus concatenation | [concatenate.py](../../src/fair_phyloflow/concatenate.py) |
| Task dependencies, validation, and resumption | [run_contract.py](../../src/fair_phyloflow/run_contract.py), [executable route contract](../EXECUTABLE_ROUTE.md) |
| Route and tool support boundaries | [route matrix](../ROUTE_MATRIX.md), [tool adapters](../TOOL_ADAPTERS.md) |
| Reporting and provenance | [reporting.py](../../src/fair_phyloflow/reporting.py), [provenance.py](../../src/fair_phyloflow/provenance.py) |
| Packaging and verification | [packaging.py](../../src/fair_phyloflow/packaging.py) |
| Planned data layers and scientific validation | [data support](../DATA_SUPPORT.md), [roadmap](../ROADMAP.md) |

## Relationship to the existing presentation slide

The root-level `presentation_fair_phyloflow_workflow.svg` is retained as a
separate presentation asset. It gives a short linear narrative and includes
run-specific demonstration counts. This overview avoids run-specific counts
and adds the scientific dependency structure, implementation boundaries, and
workflow-wide evidence mechanisms needed to represent the repository.
