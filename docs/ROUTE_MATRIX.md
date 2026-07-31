# Route Matrix

FAIR PhyloFlow records route choice explicitly and distinguishes guidance,
command generation, direct execution, and parsed outputs.

| Route ID | Prepared input used now | Decision support | Generated tool material | Direct execution | Parsed/normalized outputs |
| --- | --- | --- | --- | --- | --- |
| `concatenation` | locus alignments | implemented | IQ-TREE 2 and RAxML-NG commands | IQ-TREE 2 | IQ-TREE tree/support summary |
| `gene_tree` | locus alignments | implemented | per-locus IQ-TREE 2 and ParGenes commands | IQ-TREE 2 gene trees plus gCF/sCF | IQ-TREE results and normalized branch concordance |
| `species_tree` | gene-tree input is registered but not consumed | implemented | illustrative ASTRAL guidance | no | no |
| `conflict` | specialized downstream inputs are not consumed | implemented warnings | BUCKy guidance | no | no |

The `gene_trees` input mode currently validates only that its configured
directory exists and uses that mode for route recommendation. It does not yet
enumerate, validate, combine, or analyze the supplied tree files.

Concordance is fully automated only in the prepared-alignment IQ-TREE 2 route,
where FAIR PhyloFlow creates and validates the reference tree and per-locus
gene trees before running gCF and sCF. Other concordance or conflict workflows
remain guidance or future work.

See [ANALYSIS_CAPABILITIES.md](ANALYSIS_CAPABILITIES.md) for scientific scope
and [TOOL_ADAPTERS.md](TOOL_ADAPTERS.md) for support-level definitions.
