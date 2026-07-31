from __future__ import annotations

from fair_phyloflow.adapters.astral import AstralAdapter
from fair_phyloflow.adapters.base import ToolAdapter
from fair_phyloflow.adapters.bucky import BuckyAdapter
from fair_phyloflow.adapters.busco import BuscoAdapter
from fair_phyloflow.adapters.iqtree import IQTreeAdapter
from fair_phyloflow.adapters.pargenes import ParGenesAdapter
from fair_phyloflow.adapters.raxml_ng import RaxmlNGAdapter
from fair_phyloflow.config import WorkflowConfig
from fair_phyloflow.domain import DomainPackMetadata


class PhylogenomicsDomainPack:
    def metadata(self) -> DomainPackMetadata:
        return DomainPackMetadata(
            pack_id="phylogenomics",
            label="Phylogenomics",
            description="Decision-aware phylogenomic analysis from curated accessions and prepared alignments.",
            configuration_version="1",
        )

    def adapters(self, cfg: WorkflowConfig) -> list[ToolAdapter]:
        adapters: list[ToolAdapter] = [
            IQTreeAdapter(),
            RaxmlNGAdapter(),
            ParGenesAdapter(),
            AstralAdapter(),
            BuscoAdapter(),
        ]
        if cfg.domain_profile.value in {"fungi", "bacteria", "generic"}:
            adapters.append(BuckyAdapter())
        return adapters
