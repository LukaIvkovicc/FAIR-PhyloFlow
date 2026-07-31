# FAIR PhyloFlow Workflow Specification

This specification encodes FAIR PhyloFlow's operational contract: a
**FAIR, standardized, decision-based, user-guiding** workflow for reproducible
phylogenomics from curated data.

## Non-Negotiables

- The contribution is **workflow design + decision logic + provenance**, not a
  new inference algorithm.
- Focus on **curated data reuse** in the MVP.
- Route selection must be explicit: **what is valid, what is recommended, and
  why**.
- Workflow decisions must control downstream execution. For example, excluded
  loci are reported and preserved as evidence, but they must not enter
  concatenation or per-locus inference inputs.
- **Concordance is cross-cutting** interpretive information, not "just another
  route."
- FAIRness is embedded throughout via traceable decisions and machine-readable
  outputs.

## Seven User-Facing Stages

1. Define biological question, scope, input mode
2. Locate/register/select curated resources (include/exclude; outgroup explicit)
3. Readiness, assumptions, locus suitability
4. Choose analytical route + tools
5. Construct tree / tree set
6. Interpret support vs concordance; flag conflict/unresolved
7. Capture provenance + reusable outputs package

## Operational Shape

The current implementation is an ETL-style workflow:

- **Extract** curated accessions, taxa tables, per-locus alignments, configs, and
  detected tool outputs.
- **Transform** them into normalized registries, readiness states, locus
  metrics, route recommendations, commands, reports, and provenance.
- **Load** those artifacts into staged output folders and a reusable FAIR
  package.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the implementation-level workflow
and ETL contract.

## Current Milestone

The current repository implements one executable vertical slice from prepared
alignments:

```text
prepared alignments
-> selected loci
-> concatenated tree
-> per-locus gene trees
-> concordance-aware interpretation
-> report and FAIR package
```

This keeps the project focused: prove the alignment-to-concordance workflow
before expanding into raw reads, genome download, ortholog inference, or a full
graphical workbench.
