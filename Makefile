.PHONY: help install format lint type test coverage build check demo clean

PYTHON ?= python

help:
	@echo "install   Install the package and development dependencies"
	@echo "format    Apply safe formatting fixes"
	@echo "lint      Check source, tests, and app with Ruff"
	@echo "type      Type-check the package"
	@echo "test      Run the test suite"
	@echo "coverage  Run tests with branch coverage"
	@echo "build     Build and validate distributions"
	@echo "check     Run lint, type, coverage, and build checks"
	@echo "demo      Generate the complete no-execution demo output"
	@echo "clean     Remove generated local build and quality artifacts"

install:
	$(PYTHON) -m pip install -e ".[dev,ui]"

format:
	$(PYTHON) -m ruff check --fix src tests app
	$(PYTHON) -m ruff format src tests app

lint:
	$(PYTHON) -m ruff check src tests app
	$(PYTHON) -m ruff format --check src tests app

type:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest

coverage:
	$(PYTHON) -m pytest --cov=fair_phyloflow --cov-branch --cov-report=term-missing --cov-report=xml

build:
	$(PYTHON) -m build --no-isolation
	$(PYTHON) -m twine check dist/*

check: lint type coverage build

demo:
	$(PYTHON) -m fair_phyloflow.cli check examples/demo_project/project.yaml
	$(PYTHON) -m fair_phyloflow.cli status examples/demo_project/project.yaml
	$(PYTHON) -m fair_phyloflow.cli plan examples/demo_project/project.yaml
	$(PYTHON) -m fair_phyloflow.cli run examples/demo_project/project.yaml --no-execute
	$(PYTHON) -m fair_phyloflow.cli report examples/demo_project/project.yaml
	$(PYTHON) -m fair_phyloflow.cli package examples/demo_project/project.yaml

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; [shutil.rmtree(Path(p), ignore_errors=True) for p in ('build', 'dist', '.mypy_cache', '.pytest_cache', '.pytest_tmp', '.ruff_cache', 'htmlcov')]; [shutil.rmtree(p, ignore_errors=True) for p in Path('.').rglob('__pycache__')]; [shutil.rmtree(p, ignore_errors=True) for p in Path('.').rglob('*.egg-info')]; [Path(p).unlink(missing_ok=True) for p in ('.coverage', 'coverage.xml')]"
