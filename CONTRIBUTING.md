# Contributing

FAIR PhyloFlow is a research prototype. Contributions should
preserve its central principle: make scientific workflow decisions explicit
instead of hiding them behind one-click automation.

## Before You Start

- Search existing issues before opening a new one.
- Open an issue before undertaking a large feature or scientific-method change.
- Do not commit confidential, unpublished, restricted, or personally
  identifiable research data.
- Use focused branches and pull requests.

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security
issues must follow [SECURITY.md](SECURITY.md).

## Development Setup

```bash
python -m pip install -e ".[dev]"
make check
```

`make check` runs formatting checks, linting, static typing, branch coverage,
package building, and distribution validation. Use `make format` to apply the
project formatter and safe lint fixes.

Before opening a pull request:

```bash
make check
make demo
```

Every behavior change should include a focused regression test. Tests should be
deterministic and must not require network access or proprietary external tools.

## Documentation Rule

Every workflow feature should update the relevant documentation:

- new data type -> `docs/DATA_SUPPORT.md`
- new route or analysis behavior -> `docs/ANALYSIS_CAPABILITIES.md`
- new tool adapter -> `docs/TOOL_ADAPTERS.md`
- changed output structure -> `docs/ARCHITECTURE.md`
- new validation example -> `docs/VALIDATION_GUIDE.md` and `docs/ROADMAP.md`

Public documentation should describe implemented behavior in the present tense
and planned behavior explicitly as planned. Avoid claims that a command scaffold
is equivalent to validated execution or biological interpretation.

## Adapter Rule

Tool adapters should declare:

- required input layer;
- compatible route;
- support level;
- command template;
- expected outputs;
- parser behavior, if any;
- provenance fields.

## Scientific Rule

The workflow may recommend routes and flag limitations, but it should not make
unsupported biological conclusions. Species-delimitation or reticulation claims
must remain user-interpreted unless a validated downstream method is explicitly
implemented.

## Pull Request Expectations

CI runs tests on Python 3.11–3.14, including Streamlit button and error handling
tests. Install `.[dev,ui]` to run that complete suite locally. It also checks
lint, formatting, types, distribution installation, the real IQ-TREE 2 route,
and container startup through the image's health check.

Dependabot checks Python, GitHub Actions, Docker, and Conda dependencies monthly.
IQ-TREE major updates need a deliberate execution-contract review; the Conda
updater does not propose those automatically. Review dependency pull requests
and their CI results before merging.

A pull request should explain:

- the user or research problem;
- the resulting behavior;
- how it was tested;
- whether decisions, outputs, provenance, or interpretation changed;
- any compatibility or documentation implications.

Maintainers may request smaller changes when a proposal combines unrelated
scientific and software concerns.
