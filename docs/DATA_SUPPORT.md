# Data Support Model

Phylogenomics data are multidimensional. FAIR PhyloFlow therefore distinguishes
between **input mode** and **data type**.

- `input.mode` describes how the user enters the workflow.
- `input.data_type` describes the biological/computational layer represented by
  the data.

This distinction keeps route selection honest. For example, an accession table,
a proteome folder, an orthogroup table, a set of alignments, and a set of gene
trees are all valid phylogenomics inputs, but they imply very different
readiness checks, tools, assumptions, and outputs.

## Current Data Types

| Data type | Meaning | Current support |
| --- | --- | --- |
| `accessions` | Curated public identifiers and metadata | Normalize/register/report |
| `genome_assemblies` | Genome FASTA files or assembly accessions | Planned; BUSCO/download layer needed |
| `proteomes` | Predicted protein FASTA files | Planned; BUSCO/orthology layer needed |
| `orthogroups` | Ortholog tables or per-locus sequence sets | Planned; bridge to alignments |
| `locus_alignments` | Per-locus nucleotide FASTA alignments | Metrics, selection tables, concatenation, commands |
| `gene_trees` | Existing per-locus trees | Route shortcut; concordance/species-tree layer planned |
| `snp_matrix` | SNP/population-genomic matrix | Guidance only; future conflict/reticulation branch |
| `raw_reads` | FASTQ reads | Out of MVP scope; future extension |

## Recommended MVP Order

The first validation should prove the **alignments to tree/concordance report**
path, while also maintaining an accession registry for traceability.

Why this order:

- It tests the workflow's central scientific claim: tree inference alone is not
  enough; support and concordance must be interpreted together.
- It avoids getting blocked immediately by genome download, assembly,
  annotation, orthology inference, and HPC complexity.
- It still remains FAIR because accessions and source metadata can be recorded
  upstream of the alignment set.

The practical Penicillium validation should therefore have two layers:

1. A curated accession registry documenting the biological resources.
2. A small prepared alignment dataset that exercises route selection, locus
   decisions, gene-tree generation, and support/concordance interpretation.

## Future Backend Layers

The long-term backend should expand in layers:

```text
accessions
  -> genome/proteome retrieval
  -> readiness and BUSCO/completeness summaries
  -> ortholog/locus recovery
  -> per-locus alignments
  -> gene trees / concatenated trees / species trees
  -> concordance and conflict interpretation
  -> FAIR package
```

Each layer should produce explicit intermediate outputs and provenance, not just
pass files silently to the next tool.
