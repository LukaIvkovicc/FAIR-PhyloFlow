# Penicillium Camemberti Case Study Plan

This case study validates FAIR PhyloFlow against a fungal workflow scenario.
The goal is not to make a one-click taxonomic decision, but to test whether the
workflow can guide a user from curated fungal resources to explicit route
selection, locus decisions, tree/concordance outputs, and reusable provenance.

## Validation Question

Can FAIR PhyloFlow support a reproducible, concordance-aware workflow for a
Penicillium camemberti species-complex analysis, where species boundaries and
locus disagreement matter?

## Staged Implementation

1. **Accession registry**
   Build a curated table of P. camemberti and related taxa. Record taxon,
   strain, accession, source database, publication, inclusion status, and
   inclusion/exclusion reason. Initial public anchor: NCBI assembly
   `GCA_014839975.1` for P. camemberti strain FM 013, linked to the Ropars et
   al. domestication study.

2. **Readiness checks**
   Check taxon names, outgroup declaration, duplicate strains, missing metadata,
   and minimum taxon coverage. Later: consume BUSCO/completeness outputs for
   genome/proteome readiness.

3. **Locus strategy**
   Start with existing alignments or curated single-copy marker alignments.
   Record locus metrics, selected loci, and excluded loci. Avoid claiming
   automatic optimal locus choice; decisions remain explicit.

4. **Route selection**
   Species-boundary and conflict-sensitive questions should recommend a
   gene-tree route with concordance-aware interpretation. Concatenation can be
   generated as a comparison or first-pass tree, not as the only endpoint.

5. **Tree and concordance outputs**
   The executable route can run compatible IQ-TREE 2 in WSL/Linux, validate
   reference and per-locus trees, calculate gCF/sCF, and package the evidence.
   Later: biologically validate genuine curated alignments and scale inference
   with ParGenes and species-tree summaries with ASTRAL-style adapters.

6. **FAIR package**
   Include normalized accessions, locus decision tables, commands, provenance,
   methods report, environment information, and output summary.

## Success Criteria

- The workflow explains why a route is recommended.
- Every accession, locus decision, command, and output is traceable.
- The report distinguishes support from concordance.
- The case can be rerun from configuration and documented outputs.
- Limitations are visible instead of hidden behind automation.

## Current Example Scaffold

The repository now includes `examples/penicillium_camemberti_case/`.

This scaffold combines a candidate public-accession registry with tiny
synthetic control alignments. The accession-to-publication mapping requires
independent validation, and the alignments are only workflow test fixtures—not
biological evidence. Their purpose is to verify that the backend can register
resources, score loci, exclude incomplete loci, recommend a gene-tree route,
and generate reproducible commands/reports.

Run it in this order:

```bash
fair-phyloflow check examples/penicillium_camemberti_case/project.yaml
fair-phyloflow status examples/penicillium_camemberti_case/project.yaml
fair-phyloflow plan examples/penicillium_camemberti_case/project.yaml
fair-phyloflow run examples/penicillium_camemberti_case/project.yaml --no-execute
fair-phyloflow report examples/penicillium_camemberti_case/project.yaml
fair-phyloflow package examples/penicillium_camemberti_case/project.yaml
```

The next validation step is to replace the synthetic control alignments with
real single-copy ortholog alignments derived from the curated Penicillium
resources.
