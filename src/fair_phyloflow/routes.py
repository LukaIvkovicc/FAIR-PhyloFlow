from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .config import InputMode, QuestionType, WorkflowConfig


class RouteId(str, Enum):
    concatenation = "concatenation"
    gene_tree = "gene_tree"
    species_tree = "species_tree"
    conflict = "conflict"


@dataclass(frozen=True)
class RouteRecommendation:
    route: RouteId
    rationale: list[str]
    warnings: list[str]
    executable_now: bool


def recommend_route(cfg: WorkflowConfig, *, loci_count: int | None = None) -> RouteRecommendation:
    rationale: list[str] = []
    warnings: list[str] = []
    prepared_alignments = cfg.input.mode == InputMode.locus_alignments and cfg.input.alignments_dir is not None

    # Domain-profile framing (guidance only; does not hard-code methods)
    if cfg.domain_profile.value == "bacteria":
        warnings.append(
            "Bacteria profile: horizontal gene transfer/recombination can increase locus discordance; prefer concordance-aware interpretation."
        )
    elif cfg.domain_profile.value == "fungi":
        rationale.append(
            "Fungi profile: genealogical concordance is often relevant for species boundaries (GCPSR-style reasoning)."
        )

    # Entry-point shortcuts based on input mode
    if cfg.input.mode == InputMode.gene_trees:
        rationale.append(
            "Input mode registers a prepared gene-tree directory for route selection; "
            "downstream file validation and analysis are not yet automated."
        )
        if cfg.question.needs_concordance or cfg.analysis.require_concordance:
            rationale.append("Concordance-aware interpretation requested.")
        return RouteRecommendation(
            route=RouteId.gene_tree, rationale=rationale, warnings=warnings, executable_now=False
        )

    # Explicit override
    if cfg.analysis.route != "auto":
        route = RouteId(cfg.analysis.route)
        rationale.append(f"Route overridden by config: {cfg.analysis.route}.")
        return RouteRecommendation(
            route=route,
            rationale=rationale,
            warnings=warnings,
            executable_now=prepared_alignments and route in {RouteId.concatenation, RouteId.gene_tree},
        )

    qt = cfg.question.type

    if qt == QuestionType.published_tree_reanalysis:
        rationale.append(
            "Published tree reanalysis: prioritize traceable provenance, reproducible command regeneration, and explicit route/assumption documentation."
        )
        warnings.append(
            "If reproducing an existing study, pin tool versions/parameters as closely as possible; default settings may not match the publication."
        )

    if qt == QuestionType.clade_placement:
        rationale.append(
            "Clade placement: often a targeted analysis; a full genome-scale workflow may be unnecessary depending on scope."
        )
        warnings.append(
            "Consider whether a curated reference dataset/tree exists; placement/constraint-based workflows are not yet automated in MVP."
        )

    if qt in {QuestionType.species_delimitation, QuestionType.conflict_investigation}:
        rationale.append("Conflict-sensitive question type (species delimitation/conflict investigation).")
        rationale.append("Recommend gene-tree outputs to avoid over-reliance on a single concatenated topology.")
        if not (cfg.question.needs_concordance or cfg.analysis.require_concordance):
            warnings.append("Concordance not requested; consider enabling it for conflict-sensitive questions.")
        if loci_count is not None and loci_count >= cfg.analysis.large_locus_threshold:
            warnings.append(
                "Large number of loci detected; plan scalable per-locus inference (e.g., ParGenes) rather than laptop execution."
            )
        return RouteRecommendation(
            route=RouteId.gene_tree, rationale=rationale, warnings=warnings, executable_now=prepared_alignments
        )

    if qt == QuestionType.reticulate_history_screening:
        rationale.append("Question type suggests reticulation/introgression screening.")
        warnings.append("Reticulation/conflict analyses are guidance/command-generation only in MVP.")
        return RouteRecommendation(route=RouteId.conflict, rationale=rationale, warnings=warnings, executable_now=False)

    # Default broad relationships
    if not cfg.analysis.allow_concatenation:
        rationale.append("Concatenation is disabled by configuration; selecting the gene-tree route.")
        return RouteRecommendation(
            route=RouteId.gene_tree, rationale=rationale, warnings=warnings, executable_now=prepared_alignments
        )
    if cfg.question.conflict_sensitive:
        rationale.append("The question is marked conflict-sensitive; selecting the gene-tree route.")
        return RouteRecommendation(
            route=RouteId.gene_tree, rationale=rationale, warnings=warnings, executable_now=prepared_alignments
        )
    rationale.append("Defaulting to concatenation-based inference for broad relationship inference.")
    if cfg.question.needs_concordance or cfg.analysis.require_concordance:
        rationale.append("Concordance requested; will plan concordance assessment if gene trees are available.")
    if loci_count is not None and loci_count >= cfg.analysis.large_locus_threshold:
        warnings.append("Large number of loci detected; consider ParGenes for scalable per-locus inference.")
    return RouteRecommendation(
        route=RouteId.concatenation, rationale=rationale, warnings=warnings, executable_now=prepared_alignments
    )
