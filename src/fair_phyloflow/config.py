from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionType(str, Enum):
    species_delimitation = "species_delimitation"
    broad_relationship_inference = "broad_relationship_inference"
    clade_placement = "clade_placement"
    published_tree_reanalysis = "published_tree_reanalysis"
    conflict_investigation = "conflict_investigation"
    reticulate_history_screening = "reticulate_history_screening"


class InputMode(str, Enum):
    locus_alignments = "locus_alignments"
    gene_trees = "gene_trees"
    curated_accessions = "curated_accessions"


class DataType(str, Enum):
    accessions = "accessions"
    genome_assemblies = "genome_assemblies"
    proteomes = "proteomes"
    orthogroups = "orthogroups"
    locus_alignments = "locus_alignments"
    gene_trees = "gene_trees"
    snp_matrix = "snp_matrix"
    raw_reads = "raw_reads"


class DomainProfile(str, Enum):
    fungi = "fungi"
    bacteria = "bacteria"
    generic = "generic"


class ProjectConfig(StrictModel):
    name: str
    description: str | None = None
    outdir: Path = Field(default=Path("results"))


class QuestionConfig(StrictModel):
    type: QuestionType
    conflict_sensitive: bool = False
    needs_concordance: bool = False


class InputConfig(StrictModel):
    mode: InputMode
    data_type: DataType | None = None
    alignments_dir: Path | None = None
    gene_trees_dir: Path | None = None
    taxa_table: Path | None = None
    outgroup: str | None = None
    accessions_table: Path | None = None

    @model_validator(mode="after")
    def _validate_mode_paths(self) -> "InputConfig":
        if self.data_type is None:
            defaults = {
                InputMode.locus_alignments: DataType.locus_alignments,
                InputMode.gene_trees: DataType.gene_trees,
                InputMode.curated_accessions: DataType.accessions,
            }
            self.data_type = defaults[self.mode]
        if self.mode == InputMode.locus_alignments and self.alignments_dir is None:
            raise ValueError("input.alignments_dir is required for mode=locus_alignments")
        if self.mode == InputMode.gene_trees and self.gene_trees_dir is None:
            raise ValueError("input.gene_trees_dir is required for mode=gene_trees")
        if self.mode == InputMode.curated_accessions and self.accessions_table is None:
            raise ValueError("input.accessions_table is required for mode=curated_accessions")
        compatible_data_types = {
            InputMode.locus_alignments: DataType.locus_alignments,
            InputMode.gene_trees: DataType.gene_trees,
            InputMode.curated_accessions: DataType.accessions,
        }
        if self.data_type != compatible_data_types[self.mode]:
            raise ValueError(
                f"input.data_type={self.data_type.value} is incompatible with input.mode={self.mode.value}"
            )
        return self


class AnalysisPreferences(StrictModel):
    route: Literal["auto", "concatenation", "gene_tree", "species_tree", "conflict"] = "auto"
    allow_concatenation: bool = True
    require_concordance: bool = False
    large_locus_threshold: int = Field(default=500, ge=1)
    min_alignment_length: int = Field(default=1, ge=1)
    max_mean_missing_fraction: float = Field(default=0.5, ge=0.0, le=1.0)
    min_taxa_per_locus: int | None = Field(default=None, ge=3)
    threads: int | str = "AUTO"
    random_seed: int = Field(default=1729, ge=1)
    bootstrap_replicates: int = Field(default=1000, ge=0)
    concordance_quartets: int = Field(default=100, ge=1)

    @field_validator("threads")
    @classmethod
    def _validate_threads(cls, value: int | str) -> int | str:
        if isinstance(value, int):
            if value < 1:
                raise ValueError("analysis.threads must be a positive integer or 'AUTO'")
            return value
        if value.upper() != "AUTO":
            raise ValueError("analysis.threads must be a positive integer or 'AUTO'")
        return "AUTO"

    @model_validator(mode="after")
    def _validate_route_preferences(self) -> "AnalysisPreferences":
        if self.route == "concatenation" and not self.allow_concatenation:
            raise ValueError("analysis.route=concatenation conflicts with analysis.allow_concatenation=false")
        return self


class ExecutionConfig(StrictModel):
    execute_when_available: bool = True
    mode: Literal["local"] = "local"
    iqtree_bin: str = "iqtree2"
    command_timeout_seconds: int = Field(default=86400, ge=1)
    raxmlng_bin: str = "raxml-ng"
    pargenes_bin: str = "pargenes.py"
    pargenes_cores: int = Field(default=2, ge=2)
    busco_bin: str = "busco"
    busco_cores: int = Field(default=1, ge=1)
    astral_bin: str = "astral"
    bucky_bin: str = "bucky"


class FairConfig(StrictModel):
    capture_provenance: Literal[True] = True
    create_methods_report: Literal[True] = True
    package_outputs: Literal[True] = True


class WorkflowConfig(StrictModel):
    project: ProjectConfig
    domain_pack: Literal["phylogenomics"] = "phylogenomics"
    domain_profile: DomainProfile = DomainProfile.fungi
    question: QuestionConfig
    input: InputConfig
    analysis: AnalysisPreferences = Field(default_factory=AnalysisPreferences)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    fair: FairConfig = Field(default_factory=FairConfig)

    @classmethod
    def load(cls, path: Path) -> "WorkflowConfig":
        base_dir = path.resolve().parent
        data: dict[str, Any]
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        cfg = cls.model_validate(data)
        cfg.project.outdir = _resolve_relative_to(base_dir, cfg.project.outdir)
        for field in ["alignments_dir", "gene_trees_dir", "taxa_table", "accessions_table"]:
            value = getattr(cfg.input, field)
            if value is not None:
                setattr(cfg.input, field, _resolve_relative_to(base_dir, value))
        return cfg


def _resolve_relative_to(base_dir: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()
