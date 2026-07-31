# Tool Adapters

Tool adapters connect FAIR PhyloFlow's route logic to external scientific
software. Each adapter declares:

- tool identity
- compatible routes
- support level
- executable detection
- version detection
- command templates
- future parser/execution responsibilities

## Support Levels

| Level | Meaning |
| --- | --- |
| `guided` | Explains where the tool/route fits, but does not generate a complete executable workflow |
| `command` | Generates reproducible command templates |
| `executable` | Can be run directly by FAIR PhyloFlow |
| `parsed` | Outputs can be parsed and interpreted by FAIR PhyloFlow |

## Current Adapter Matrix

| Tool | Routes | Current level | Current role |
| --- | --- | --- | --- |
| IQ-TREE 2 | concatenation, gene_tree | parsed | validated reference/per-locus execution, gCF/sCF, branch evidence, resumption, and parsing |
| RAxML-NG | concatenation, gene_tree | command | alternative ML tree command templates |
| ParGenes | gene_tree | command | scalable per-locus model/tree command scaffold for many loci |
| ASTRAL | species_tree | guided | requirements plus an illustrative, unbound command scaffold |
| BUSCO | all routes as Stage 3 helper | guided | completeness/marker-suitability guidance and placeholder |
| BUCKy | gene_tree, conflict | guided | advanced Bayesian concordance guidance |

The current prepared-alignment command contract is nucleotide FASTA. Protein
alignment models, missing-data semantics, and ParGenes data-type selection are
not yet claimed by version 0.1.0.

`execution.pargenes_cores` and `execution.busco_cores` make adapter resource
examples explicit and configurable. RAxML-NG and IQ-TREE commands use the
shared analysis thread and bootstrap settings.

## User Interpretation

`fair-phyloflow status <project.yaml>` tells users which adapters are visible in
the current environment and which tools are installed. A missing tool does not
mean the workflow is invalid; it means that route is currently command-only or
guidance-only unless the user installs the required software.

## Adapter Development Contract

New adapters should define:

1. Required input data type.
2. Compatible route(s).
3. Command template.
4. Expected output files.
5. Parser behavior, if any.
6. How results should appear in reports.
7. Provenance fields that must be recorded.

This keeps the workflow extensible without hard-coding one preferred tool.
