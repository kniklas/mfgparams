# Implementation Plan: Rename Package to mfgparams

**Branch**: `012-rename-package-mfgparams` | **Date**: 2026-08-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-rename-package-mfgparams/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Rename the project's distributed Python package from `machine-calc` (distribution) /
`machine_calc` (import module) to the shorter, more generic `mfgparams`, updating every
functional reference across source, tests, docs, CI, and packaging metadata, with no change to
calculation logic, CLI behavior, or the public API — a pure identifier rename, verified by an
automated repo-wide reference check and a full green test suite under the new name.

## Technical Context

**Language/Version**: Python >=3.9 (per current `pyproject.toml` `requires-python`; unchanged)

**Primary Dependencies**: None added or removed. Existing runtime dep (`tomli` for <3.11) and
dev-toolchain deps (pytest, pytest-cov, ruff, black, mypy, sphinx, bandit, radon, xenon,
pip-audit) are unaffected except where their config references the package path by name.

**Storage**: N/A (no persistent storage; config/reference data are bundled TOML files under
`src/<package>/**/data/*.toml`, unaffected in content, only their parent path changes)

**Testing**: pytest (existing suite under `tests/{unit,contract,integration,static,performance,scripts}`),
extended with a new static verification test asserting no stray old-name references remain
(FR-008)

**Target Platform**: Cross-platform CLI/library (Linux/macOS/Windows), including the
legacy/low-power hardware profile required by Constitution Principle V — unaffected by this
rename

**Project Type**: Single project, `src/` layout library + CLI (unchanged structure, renamed
package directory)

**Performance Goals**: N/A — no calculation or runtime-path change; this is an identifier rename

**Constraints**: No backward-compatibility alias/shim (per spec FR-006); the rename MUST be
delivered atomically (see Structure Decision) so `main` is never left in a half-renamed state,
because every merge to `main` triggers an automated PyPI release (Constitution "Additional
Constraints")

**Scale/Scope**: ~174 files referencing `machine_calc` and ~32 referencing `machine-calc` across
`src/`, `tests/`, `docs/`, `specs/`, `.github/`, `scripts/`, and root packaging/config files
(measured via repo-wide grep at planning time); no change in line-of-code count beyond the
rename itself

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Assessment |
|---|---|---|
| I. Code Quality | Rename must not degrade readability/consistency | PASS — mechanical identifier rename only; no logic restructuring, no god-functions introduced |
| II. Testing Standards (NON-NEGOTIABLE) | Full suite must pass; new behavior needs tests | PASS — no new calculation behavior to test; FR-005/FR-008 require the existing suite to stay green under the new name plus one new static reference-check test |
| III. Calculation Robustness | No calculation change | PASS (N/A) — no formula, validation, or numeric-handling code is touched |
| IV. Python Packaging & Versioning | `pyproject.toml` single source of truth, `src/` layout, single version location | PASS — distribution `name` and the `src/<package>/__init__.py` single-source version pointer both move together; still one canonical version location, just renamed |
| V. Resource-Constrained Compatibility | No new/heavier dependencies, footprint unchanged | PASS — zero dependency changes |
| VI. Extensibility by Design | Per-operation module boundaries preserved | PASS — `operations/{drilling,milling}` internal structure is unchanged, only the top-level package name wrapping it |
| VII. Documentation & Publishing | Sphinx docs stay buildable and accurate; README badges stay valid | PASS, with care — Sphinx `conf.py` and autodoc module paths must be updated to `mfgparams.*`; README/coverage/build badges are unaffected because they key off the *repository* slug, not the package name (see Clarifications exclusion) |
| VIII. Internationalization | Message-catalog mechanism unaffected | PASS — `locales/` moves with the package directory; message keys and catalog format unchanged |
| IX. Automated Quality/Security Gates | CI gates (lint, type-check, complexity, bandit, pip-audit, CodeQL) must keep passing | PASS, with care — tool configs that hard-code the old path (`mypy` `files`, coverage `source`/`--cov`, radon/xenon targets, bandit target dir) must be repointed at `src/mfgparams` or the gate silently stops checking anything |
| X. Licensing & Author Rights | License metadata/notices stay accurate | PASS — `LICENSE.md`'s copyright/repo-link line is a repository URL, not a package-name reference, so it is unaffected (see spec Clarifications exclusion); `pyproject.toml` `license`/`license-files` fields are untouched by this rename |
| XI. Multi-Agent Coding-Tool Consistency | No hand-patching of generated per-agent files | PASS, with care — old-name mentions live only in the hand-authored `.github/skills/*` docs (the constitution's explicit symlink-shared exception), never in generated `.github/agents/*`/`.github/prompts*`/`.claude/skills/speckit-*` files (verified: those contain no project-specific package name); only the hand-authored skill docs are edited, never the generated integration output |
| XII. Long-Lived Feature Branches for Multi-PR Work | Large/risky features need an integration branch | NOT TRIGGERED — see Structure Decision: this feature is delivered as a single atomic PR, so the multi-PR integration-branch machinery does not apply |

No violations requiring a Complexity Tracking entry.

**Post-Phase-1 re-check**: After producing `research.md`, `data-model.md`,
`contracts/package-identity-contract.md`, and `quickstart.md`, the table above still holds — the
Phase 1 design didn't surface any new gate risk (e.g., no new dependency, no new architecture
layer, no license-text change); it only made explicit *how* Principles VII, IX, X, and XI stay
satisfied (autodoc path updates, CI tool-config repointing, the repo-URL exclusion, and the
hand-authored-skill exception, respectively). Gate status unchanged: all PASS.

## Project Structure

### Documentation (this feature)

```text
specs/012-rename-package-mfgparams/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── package-identity-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Single project, src/ layout — package directory renamed in place, internal shape unchanged.
src/
├── mfgparams/                    # renamed from machine_calc/
│   ├── __init__.py               # single-source version pointer (unchanged mechanism)
│   ├── __main__.py
│   ├── cli.py
│   ├── i18n.py
│   ├── models.py
│   ├── registry.py
│   ├── registry_config.py
│   ├── units.py
│   ├── validation.py
│   ├── locales/
│   └── operations/
│       ├── drilling/
│       └── milling/
│           ├── end_milling/
│           └── face_milling/
└── mfgparams.egg-info/           # generated at build time — regenerated, never hand-renamed

tests/
├── unit/          # imports updated: `from mfgparams import ...`
├── contract/      # imports updated
├── integration/   # imports updated
├── static/        # + new reference-check test (FR-008)
├── performance/   # imports updated
└── scripts/       # imports updated

docs/source/        # Sphinx autodoc targets updated to mfgparams.*; conf.py project name updated

.github/workflows/ci.yml   # tool-config paths (mypy/coverage/bandit/radon targets) repointed

pyproject.toml       # [project].name, [project.scripts], [tool.setuptools.dynamic].version,
                      # [tool.setuptools.package-data], [tool.pytest.ini_options].addopts,
                      # [tool.coverage.run].source, [tool.mypy].files all repointed to mfgparams
```

**Structure Decision**: Single project, unchanged `src/` layout — only the package directory
and every internal reference to its name change; no new projects, services, or top-level
directories are introduced. Delivered as **one atomic pull request directly to `main`**, not a
Principle XII long-lived integration branch: this feature's tasks are mechanical and uniform
(rename + verify), sized to fit one reviewable PR, and — critically — a half-renamed
intermediate state would either (a) break imports/CI on `main` between sub-PRs, or (b) get
auto-published to PyPI in a broken state, since every merge to `main` triggers a release per the
constitution's Additional Constraints. Splitting this into sub-PRs against a long-lived branch
would only reintroduce that same atomicity problem one level removed, for no benefit on a
feature this uniform in shape. `git mv` is used for the package directory itself so history is
preserved; every other change is a same-file text edit.

## Complexity Tracking

*No Constitution Check violations — this section is intentionally empty.*
