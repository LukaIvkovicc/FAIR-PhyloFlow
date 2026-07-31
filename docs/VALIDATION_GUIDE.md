# Validation And Adoption Guide

This guide helps researchers, scientific developers, and contributors validate
FAIR PhyloFlow before adoption or extension.

## What To Validate

The current repository is an **executable phylogenomics workflow prototype**,
not a finished raw-data-to-publication system. Validate:

- explicit biological-question capture
- curated resource registration
- readiness checks
- locus metrics and exclusion reasoning
- route recommendation
- route-aware tool command generation
- selected-locus-only execution inputs
- basic support/concordance output detection when files exist
- validated, resumable IQ-TREE 2 alignment-to-concordance execution when the
  compatible binary is installed
- provenance capture
- reusable report/package generation

## Fast Validation Path

Install:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Run the Penicillium validation scaffold:

```bash
fair-phyloflow check examples/penicillium_camemberti_case/project.yaml
fair-phyloflow status examples/penicillium_camemberti_case/project.yaml
fair-phyloflow plan examples/penicillium_camemberti_case/project.yaml
fair-phyloflow run examples/penicillium_camemberti_case/project.yaml --no-execute
fair-phyloflow execute examples/penicillium_camemberti_case/project.yaml --plan-only
fair-phyloflow report examples/penicillium_camemberti_case/project.yaml
fair-phyloflow package examples/penicillium_camemberti_case/project.yaml
```

Inspect:

```text
results/penicillium_camemberti_case/
|-- 02_resources/accessions_normalized.tsv
|-- 03_loci/locus_metrics.tsv
|-- 03_loci/selected_loci.tsv
|-- 03_loci/excluded_loci.tsv
|-- 04_route/recommended_route.txt
|-- 04_route/reproducible_commands.sh
|-- 05_trees/concatenated_alignment.fasta
|-- 05_trees/selected_loci_alignments/
`-- 07_fair_package/
    |-- report.md
    |-- report.html
    |-- project.snapshot.json
    |-- provenance.json
    |-- manifest-sha256.tsv
    `-- ro-crate-metadata.json
```

Then verify the completed package:

```bash
fair-phyloflow verify-package \
  results/penicillium_camemberti_case/07_fair_package
```

## Expected Behavior

The Penicillium scaffold should:

- register curated accession metadata
- detect the fungal/species-delimitation context
- recommend a gene-tree route
- classify one synthetic control locus as excluded because it lacks the outgroup
- use selected loci only for concatenation and per-locus command staging
- generate reproducible command templates
- write a structured execution plan without IQ-TREE, or generate validated
  gCF/sCF and normalized branch evidence when IQ-TREE execution completes
- write provenance and report artifacts

## Important Limitations

The current Penicillium alignments are synthetic control alignments. They are
not biological evidence. The example tests workflow mechanics, not taxonomy.

The prototype does not yet automate genome download, BUSCO parsing, ortholog
inference, or full species delimitation.

## Adoption Questions

Before adopting or extending the workflow, ask:

- Does the workflow preserve immutable outputs with checksums and provenance?
- Are phylogenomics decisions explicit and scientifically reviewable?
- Can tools or routes be extended without weakening evidence integrity?
- Are implemented, command-only, and planned capabilities distinguishable?
- Can a recipient verify a package without trusting the producing workstation?

## Project Takeaway

IQ-TREE is one adapter in FAIR PhyloFlow. The project value is the explicit
decision and evidence lifecycle around phylogenomics tools, not a new tree
inference algorithm.
