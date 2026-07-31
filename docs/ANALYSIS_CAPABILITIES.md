# Analysis Capabilities

FAIR PhyloFlow supports analyses by **workflow route**, not by pretending that
one tool can solve every phylogenomics question.

## Current User Questions

| Question type | Typical user goal | Recommended route behavior |
| --- | --- | --- |
| `broad_relationship_inference` | infer a first-pass genome-scale relationship tree | concatenation first; concordance optional if loci/gene trees exist |
| `species_delimitation` | evaluate species-boundary evidence | gene-tree route; concordance strongly recommended |
| `clade_placement` | place focal taxa in a curated reference context | guided now; placement/constraint workflow later |
| `published_tree_reanalysis` | reproduce or audit an existing study | provenance-first; command regeneration and parameter pinning |
| `conflict_investigation` | ask whether loci support different histories | gene-tree route; concordance/conflict summaries |
| `reticulate_history_screening` | screen possible introgression/hybridization/HGT | guidance now; advanced tools later |

## Current Routes

### Concatenation-Based ML Tree

Current support:

- concatenate per-locus FASTA alignments
- generate IQ-TREE and RAxML-NG commands
- optionally run IQ-TREE when available
- parse basic IQ-TREE output if present

Best for:

- first-pass relationship inference
- comparison against gene-tree/concordance routes
- datasets where a single dominant topology is plausible

Limitations:

- a highly supported concatenated tree may still hide locus conflict
- not sufficient alone for conflict-sensitive species-boundary questions

### Gene-Tree / Concordance-Aware Route

Current support:

- compute locus metrics
- select/exclude loci with explicit reasons
- generate per-locus IQ-TREE commands
- execute a content-addressed, locked, resumable IQ-TREE 2 route
- validate and deterministically collect one tree per selected locus
- calculate separate gCF and sCF evidence and normalize it by branch ID
- generate scalable ParGenes command templates for many-locus datasets
- parse IQ-TREE concordance summaries if present

Best for:

- species delimitation
- conflict investigation
- fungal GCPSR-style reasoning
- support-versus-concordance interpretation

Limitations:

- gene-tree generation is executable when compatible IQ-TREE 2
  (`>=2.2.2,<3`) is installed
- concordance requires a reference tree plus gene trees

### Species-Tree Route

Current support:

- route-level guidance
- an illustrative ASTRAL command scaffold whose gene-tree input is not yet
  wired or validated by the workflow

Best for:

- gene-tree/species-tree comparison
- datasets where incomplete lineage sorting may matter

Limitations:

- not yet executable/parsed by the workflow
- requires prepared gene trees

### Conflict / Reticulation Route

Current support:

- guidance and warnings
- BUCKy guidance for Bayesian concordance-style use cases

Best for:

- advanced biological questions about introgression, hybridization,
  recombination, HGT, or reticulate history

Limitations:

- not yet an executable route
- requires specialized data types and expert interpretation

## What A Curated Dataset Can Do Today

If users provide curated accessions only:

- register and normalize resources
- document source metadata and inclusion logic
- assess basic readiness
- recommend likely analytical routes
- create a provenance/report package

If users provide curated accessions plus alignments:

- do everything above
- score loci
- select/exclude loci transparently
- recommend route from the biological question
- generate reproducible commands
- optionally run IQ-TREE
- create tree/concordance-aware reports if outputs exist

If users provide gene trees:

- validate that the configured gene-tree directory exists
- use the input mode when recommending a route
- preserve the configured source label in the portable project snapshot

FAIR PhyloFlow does not yet enumerate, validate, combine, or analyze
user-provided gene-tree files. Concordance and species-tree execution from that
input mode remain planned.

## Not Yet Supported As Full Automation

- raw FASTQ to assembly
- genome annotation
- automated ortholog inference
- automatic genome download from accessions
- automatic BUSCO execution/parsing
- automatic species delimitation decisions
- full introgression/reticulation analysis

These are planned layers, not hidden behavior.
