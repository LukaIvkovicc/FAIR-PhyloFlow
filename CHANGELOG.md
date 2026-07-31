# Changelog

All notable changes to FAIR PhyloFlow will be documented in this file.

The project follows [Semantic Versioning](https://semver.org/) and uses the
structure recommended by [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Repository governance, citation, security, and contribution metadata.
- Automated quality, test, coverage, package-build, and container-build checks.
- Reproducible developer commands through `Makefile`.
- Content-addressed, immutable JSON execution plans with argument arrays.
- Resumable task state and output validation for the IQ-TREE 2 reference-tree,
  per-locus-tree, gCF, and sCF route.
- SHA-256 FAIR package manifests and RO-Crate-compatible metadata.
- Real and simulated IQ-TREE integration contracts with enforced 80% branch
  coverage.
- Immutable staged locus inputs and input manifests.
- Exclusive run locks with same-host stale-lock recovery.
- Checksum-aware recursive invalidation of changed scientific evidence.
- Portable configuration snapshots and FAIR-package integrity verification.
- Fresh, atomic FAIR-package assembly with latest-run selection and
  privacy-safe path redaction in packaged execution records.
- FAIR PhyloFlow product framing and an explicit internal boundary between
  phylogenomics decisions and reusable evidence mechanics.
- Configuration-driven phylogenomics workflow prototype.
- Curated-accession registration and readiness checks.
- Locus metrics, explicit selection decisions, and selected-locus concatenation.
- Route-aware adapters and reproducible command generation.
- IQ-TREE result and concordance parsing scaffolds.
- Markdown/HTML reporting and provenance-oriented FAIR output packaging.
- Demonstration projects and core regression tests.

### Fixed

- Invalid and unequal-length alignments are excluded with explicit reasons.
- Missing accession and taxon identifiers no longer become literal `nan`
  records.
- Provenance respects the configured IQ-TREE executable and reports clean Git
  state correctly.
- IQ-TREE compatibility is now an application-owned, non-overridable contract.
- Configuration typos, contradictory modes, invalid numeric bounds, and
  disabled mandatory FAIR-package artifacts are rejected.
- Generated IQ-TREE command scripts honor configured replicates and seeds and
  safely quote paths.
- Reports prefer authoritative structured-run outputs and expose normalized
  concordance evidence.
- Run identity includes the execution-contract schema, preventing collisions
  with immutable runs created by an older contract.
- FAIR-package verification now requires the core report, provenance, and
  configuration evidence and checks complete RO-Crate file coverage.
- The legacy optional-execution command omits disabled bootstrap arguments and
  propagates external-tool failures through its exit status.
- Report discovery rejects unsafe or external latest-run references.
- Fresh development installs include their build backend and constrain NumPy to
  a release whose type declarations support the Python 3.11 checking target.
- Package licensing metadata uses the current SPDX-based standard.
- ASTRAL and BUSCO scaffolds are labeled as guided rather than executable
  command integrations.
- External command generation is adapter-owned: ParGenes uses its supported
  core/data/model options, RAxML-NG honors configured bootstrap replicates, and
  BUSCO guidance honors configured executable and core settings.
