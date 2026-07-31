# Roadmap

This roadmap grows FAIR PhyloFlow from a prepared-alignment vertical mode into
a more complete, validated phylogenomics workflow.

## Phase 0: Current Prototype

Status: implemented.

- YAML configuration
- config-relative paths for portable examples
- readiness checks
- accession normalization
- locus metrics
- selected-locus-only concatenation and command staging
- route recommendation
- command generation
- tool status reporting
- IQ-TREE output/concordance parser scaffold
- provenance JSON
- HTML/Markdown reports
- Penicillium validation scaffold with synthetic control alignments
- content-addressed structured execution plans and resumable task state
- validated reference-tree, per-locus-tree, gCF, and sCF task contract
- SHA-256 evidence manifests and RO-Crate-compatible package metadata
- portable configuration snapshots and local FAIR-package verification
- enforced branch coverage of at least 80%

## Phase 1: Prepared-Alignment Executable Route

Status: implemented for prepared alignments; real-binary CI confirmation and
additional compatibility testing remain.

Implemented route:

```
prepared locus alignments
-> readiness and locus checks
-> selected loci only
-> concatenated IQ-TREE tree
-> per-locus IQ-TREE gene trees
-> IQ-TREE concordance factors when possible
-> parsed support/concordance outputs
-> report
-> FAIR package
```

Tasks:

- validate the executable route against additional supported IQ-TREE 2 patch
  releases
- add explicit retry/archive controls for invalid completed tasks
- add resource monitoring and HPC-oriented execution providers

## Phase 2: Real Penicillium Validation

Goal: replace synthetic alignments with real single-copy ortholog alignments or
existing gene-tree/concordance outputs.

Tasks:

- curate a stronger Penicillium accession table
- document source publications and strain identities
- add real alignment/gene-tree input mode example
- run IQ-TREE in WSL/Linux
- parse real support/concordance outputs
- improve interpretation tables in reports

## Phase 3: FAIR Package Hardening

Goal: make outputs more reusable and machine-actionable.

Tasks:

- add decision log
- add command manifest
- expand RO-Crate metadata beyond the current compatible core
- add stronger semantic validation against external RO-Crate tooling

## Phase 4: Upstream Data Automation

Goal: connect accession-level resources to analysis-ready data.

Tasks:

- genome/proteome download from accessions
- BUSCO execution and parsing
- ortholog/locus recovery layer
- alignment generation hooks
- explicit failure states for missing metadata or incomplete resources

## Phase 5: Advanced Routes

Goal: expand beyond the IQ-TREE-centered MVP.

Tasks:

- ParGenes execution support
- ASTRAL execution and parsing
- improved gene-tree input handling
- advanced conflict/reticulation guidance
- optional reticulation tool adapters where data types justify them

## Phase 6: Guided Phylogenomics UI

Goal: provide a guided workbench over the reproducible FAIR PhyloFlow backend.

Tasks:

- project wizard
- workflow capability discovery
- config editor
- readiness dashboard
- route recommendation view
- command preview
- report viewer
- FAIR package download

The UI should sit on top of the reproducible CLI backend, not replace it.
