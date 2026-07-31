# Penicillium Camemberti Validation Scaffold

This example validates FAIR PhyloFlow against a fungal workflow scenario.

It has two layers:

1. A candidate accession registry with public Penicillium identifiers relevant
   to the P. camemberti species complex.
2. Tiny synthetic control alignments that exercise the workflow mechanics.

The control alignments are **not biological results**. They exist only to test
the workflow path from alignment input to locus decisions, route recommendation,
command generation, reports, and FAIR packaging. Replace them with real
ortholog alignments before drawing biological conclusions.

The candidate accession metadata is included to exercise provenance handling;
it must be independently checked against authoritative repositories and source
publications before it is treated as a biological dataset.

## Commands

```bash
fair-phyloflow check examples/penicillium_camemberti_case/project.yaml
fair-phyloflow status examples/penicillium_camemberti_case/project.yaml
fair-phyloflow plan examples/penicillium_camemberti_case/project.yaml
fair-phyloflow run examples/penicillium_camemberti_case/project.yaml --no-execute
fair-phyloflow report examples/penicillium_camemberti_case/project.yaml
fair-phyloflow package examples/penicillium_camemberti_case/project.yaml
```

## Next Biological Step

Replace `alignments/` with real single-copy ortholog alignments derived from
the curated resources, then run IQ-TREE and concordance analysis in WSL/Linux.
