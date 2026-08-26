# Implementation Plan: Verified Multi-Python-Version Local & CI Testing

**Branch**: `013-tox-multi-python-testing` | **Date**: 2026-08-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/013-tox-multi-python-testing/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See
`.specify/templates/plan-template.md` for the execution workflow.

## Summary

`pyproject.toml`'s `dev` extra unconditionally pins `setuptools>=83.0.0`, which itself
requires Python ≥3.10 — so `pip install -e ".[dev]"` cannot resolve on Python 3.9, even
though `requires-python`, the trove classifiers, and the README all claim 3.9+ support.
Separately, CI's `test` job runs on a single pinned Python version (3.11), so that claimed
range is never actually verified anywhere. This feature (1) splits the `setuptools`
constraint the same way `black` is already split in the same extra, so dev-dependency
installation succeeds on every version in the supported range; (2) adds a `tox` environment
per supported version (`py39`-`py312`) running the exact `pytest --cov` command CI uses, with
`skip_missing_interpreters = true` so contributors without every interpreter get a clear
skipped/available report rather than a hard failure; (3) expands the CI `test` job into a
`fail-fast: false` matrix over the same four versions, so each version reports as a distinct,
individually-attributable required check; and (4) documents the pip-upgrade prerequisite the
plain (non-tox) install path needs on interpreters whose bundled `pip` predates PEP 660
editable-install support.

## Technical Context

**Language/Version**: Python 3.9, 3.10, 3.11, 3.12 (the project's existing declared
`requires-python`/classifier range — unchanged; this feature verifies and enforces that
range rather than widening or narrowing it)

**Primary Dependencies**: `tox>=4` (new, added to `[project.optional-dependencies].dev`);
corrected `setuptools` version constraint (existing dependency, constraint split by Python
version, mirroring the existing `black` split in the same extra); no other new dependency

**Storage**: N/A — this feature is packaging-metadata, dev-tooling, and CI configuration only

**Testing**: One new committed static test
(`tests/static/test_python_version_consistency.py`, research.md #7) guards FR-008's
version-lists-stay-in-sync requirement going forward; otherwise no new application test suite.
Validation is via `quickstart.md`'s runnable local (`tox`) and CI (matrix job) scenarios,
matching spec.md's acceptance scenarios; the project's existing test suite and ≥90% coverage
gate are exercised unchanged, now across four interpreters instead of one

**Target Platform**: Local contributor machines (any OS `tox`/`pyenv` supports) and GitHub
Actions (`ubuntu-latest` runners) — same platforms already in use, no new target

**Project Type**: Single project — dev-tooling/CI configuration layered onto the existing
single Python package; no new application module or source directory

**Performance Goals**: N/A (not a user-facing runtime requirement; out of scope for
Constitution Principle V, which governs the *application's* runtime, not CI/local-tooling
duration). CI cost is a known, accepted tradeoff (spec.md Assumptions) — the `test` job now
runs 4x, matching the 4 supported interpreters.

**Constraints**: MUST NOT change the existing test suite's behavior, the ≥90% coverage
threshold, or which suites are opt-in (spec.md Assumptions); MUST NOT change the currently
declared supported-version range (spec.md Assumptions); the local multi-version workflow
MUST NOT hard-fail its overall run solely because a supported interpreter is missing from the
contributor's machine (spec.md FR-004)

**Scale/Scope**: One new dev dependency (`tox`), one new config file (`tox.ini`), one
corrected dependency constraint (`pyproject.toml`), one committed static test guarding against
future version-list drift (`tests/static/test_python_version_consistency.py`, research.md #7),
one CI job converted to a 4-way matrix (`.github/workflows/ci.yml`), a documentation update
(`README.md`), and a required-status-check-list update in the repository's branch-protection
ruleset (a GitHub setting, not a version-controlled file — see `contracts/`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Code Quality | Linting MUST pass in CI (unaffected — no `src/` changes) | PASS (not applicable) |
| II. Testing Standards | ≥90% coverage on calculation modules, CI-enforced | PASS (unaffected) — this feature adds no calculation logic and does not change the coverage threshold or which tests run; it changes only *how many interpreters* run the identical suite |
| III. Calculation Robustness & Accuracy | N/A — no calculation logic touched | PASS (not applicable) |
| IV. Python Packaging & Versioning Standards | "Dependencies MUST be declared explicitly with sensible version constraints in `pyproject.toml`" | PASS — this feature's entire packaging change *is* correcting an existing constraint (`setuptools`) that was not actually satisfiable across the declared `requires-python` range; the fix follows the precedent already established for `black` in the same extra |
| V. Resource-Constrained Compatibility | "MUST remain compatible with older or long-term-stable operating system releases... MUST NOT depend on bleeding-edge OS features... kernel versions, or system libraries" (implies the declared Python 3.9 floor must actually work) | PASS — this feature's purpose is closing the gap between the claimed 3.9+ compatibility and what is actually installable/verified; it introduces no new bleeding-edge dependency |
| VI. Extensibility by Design | N/A — no operation/module architecture change | PASS (not applicable) |
| VII. Documentation & Publishing | Developer-facing setup/testing docs must stay accurate | PASS — README's "Run the tests" section is corrected/extended as part of this feature (FR-009) |
| VIII. Internationalization of User-Facing Messages | N/A — no REPL/CLI/error message changes | PASS (not applicable) |
| IX. Automated Code Quality, Complexity & Security Gates | "GitHub Actions MUST automate... the full test suite (with coverage reporting)... MUST be configured as required status checks on `main`" (Additional Constraints) | PASS — the `test` gate continues to run and block merge; it is now four distinctly-named, individually required checks instead of one (research.md), which *strengthens* this gate rather than weakening it. Requires a one-time, documented update to `main`'s branch-protection ruleset (GitHub setting, not code) to require all four new check names — same pattern as the ruleset migration already done in `003-ci-quality-security-gates` |

No violations requiring the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/013-tox-multi-python-testing/
├── plan.md                                # This file (/speckit.plan command output)
├── research.md                            # Phase 0 output (/speckit.plan command)
├── data-model.md                          # Phase 1 output (/speckit.plan command)
├── quickstart.md                          # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── multi-version-testing-contract.md  # Phase 1 output (/speckit.plan command)
├── checklists/
│   └── requirements.md
└── tasks.md                               # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
pyproject.toml                     # MODIFY: split the dev extra's `setuptools` constraint
                                    #   by python_version (mirroring the existing `black`
                                    #   split in the same extra, research.md #2); add
                                    #   `tox>=4` to `[project.optional-dependencies].dev`
                                    #   (research.md #1)

tox.ini                            # CREATE: envlist = py39, py310, py311, py312;
                                    #   skip_missing_interpreters = true (spec.md FR-004);
                                    #   each env installs the `dev` extra and runs the same
                                    #   `pytest --cov=mfgparams --cov-report=term-missing
                                    #   --cov-fail-under=90` command CI uses (research.md #1,
                                    #   #4)

tests/static/
└── test_python_version_consistency.py  # CREATE: asserts pyproject.toml's
                                    #   requires-python/classifiers, tox.ini's envlist, and
                                    #   ci.yml's matrix.python-version all enumerate the
                                    #   identical version set — an automated, committed
                                    #   safeguard for FR-008's "kept in sync if [the] range
                                    #   changes" requirement (research.md #7; data-model.md's
                                    #   Supported Version Range validation rule)

.github/
└── workflows/
    └── ci.yml                     # MODIFY: `test` job gains
                                    #   `strategy: {fail-fast: false, matrix: {python-version:
                                    #   ["3.9","3.10","3.11","3.12"]}}` (research.md #3);
                                    #   Codecov upload + `coverage_pct` output step gated to
                                    #   the single canonical leg (`3.11`, the version already
                                    #   used by every other job) to keep the
                                    #   `quality-summary` job's single-value output
                                    #   deterministic (research.md #5)

README.md                          # MODIFY: "Run the tests" section documents the pip-
                                    #   upgrade prerequisite for the plain (non-tox) install
                                    #   path on interpreters with an old bundled `pip`
                                    #   (research.md #6), and how to run `tox` to check all
                                    #   supported versions locally (FR-009)

(GitHub repository settings, not source-controlled)
└── Rules → Rulesets → "status checks" ruleset (from 003-ci-quality-security-gates)
                                    # MODIFY (manual, one-time): required-status-check list
                                    #   swaps the single "test" entry for the four matrix leg
                                    #   names ("test (3.9)", "test (3.10)", "test (3.11)",
                                    #   "test (3.12)") — contracts/multi-version-testing-
                                    #   contract.md; documented as a task, not automatable
```

**Structure Decision**: No new application module or package. This feature's entire surface
area is `pyproject.toml` dependency metadata, one new config file (`tox.ini`), one existing
CI job converted to a matrix, a README documentation update, and one manual GitHub
repository-setting change (the required-status-check list) — consistent with spec.md's
Assumptions that this feature "verifies and enforces [the] existing claim rather than
changing which [Python] versions are supported" and does not touch `src/mfgparams/`.

## Complexity Tracking

> No Constitution Check violations were identified; this section is not applicable.
