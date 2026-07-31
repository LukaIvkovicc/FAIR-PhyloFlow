from pathlib import Path

from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.routes import RouteId, recommend_route


def test_species_delimitation_defaults_to_gene_tree() -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    rec = recommend_route(cfg, loci_count=10)
    assert rec.route == RouteId.gene_tree
    assert rec.executable_now is True


def test_species_tree_override_is_not_reported_as_executable() -> None:
    cfg = WorkflowConfig.load(Path("examples/demo_project/project.yaml"))
    cfg.analysis.route = "species_tree"
    rec = recommend_route(cfg, loci_count=10)
    assert rec.route == RouteId.species_tree
    assert rec.executable_now is False
