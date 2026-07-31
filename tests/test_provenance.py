from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import fair_phyloflow.provenance as provenance_module
from fair_phyloflow.execution import safe_run_version
from fair_phyloflow.provenance import build_provenance


def test_build_provenance_has_expected_metadata(tmp_path: Path) -> None:
    cfg = tmp_path / "project.yaml"
    cfg.write_text(
        "project: {name: x}\nquestion: {type: broad_relationship_inference}\ninput: {mode: locus_alignments, alignments_dir: .}\n",
        encoding="utf-8",
    )

    prov = build_provenance(config_path=cfg, commands_script=None)
    assert prov.product_name == "FAIR PhyloFlow"
    assert prov.domain_pack == "phylogenomics"
    assert prov.fair_phyloflow_version
    assert "version" in prov.python
    assert "system" in prov.platform
    assert "iqtree2" in prov.tools
    assert "version" in prov.tools["iqtree2"]


def test_safe_run_version_ignores_failed_commands() -> None:
    assert safe_run_version([sys.executable, "-c", "import sys; print('bad version'); sys.exit(2)"]) is None


def test_provenance_uses_configured_iqtree_executable(tmp_path: Path) -> None:
    executable = tmp_path / "custom-iqtree"
    executable.write_text("#!/bin/sh\necho 'IQ-TREE multicore version 2.4.0'\n", encoding="utf-8")
    executable.chmod(0o755)
    cfg = tmp_path / "project.yaml"
    cfg.write_text(
        "project: {name: x}\n"
        "question: {type: broad_relationship_inference}\n"
        "input: {mode: locus_alignments, alignments_dir: .}\n"
        f"execution: {{iqtree_bin: '{executable}'}}\n",
        encoding="utf-8",
    )
    prov = build_provenance(config_path=cfg, commands_script=None)
    assert str(executable) in prov.tools
    assert prov.tools[str(executable)]["available"] is True


def test_clean_git_state_is_reported_as_clean(monkeypatch) -> None:
    monkeypatch.setattr(
        provenance_module,
        "which",
        lambda _name: SimpleNamespace(available=True, resolved_path="/usr/bin/git"),
    )

    def fake_run(argv: list[str]) -> tuple[int, str]:
        if argv[1] == "rev-parse":
            return 0, "abc123\n"
        return 0, ""

    monkeypatch.setattr(provenance_module, "run_argv", fake_run)
    git = provenance_module._git_info()
    assert git["commit"] == "abc123"
    assert git["dirty"] is False
