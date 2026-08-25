# Tasks: Rename Package to mfgparams

**Input**: Design documents from `specs/012-rename-package-mfgparams/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/package-identity-contract.md, quickstart.md

**Tests**: Included — FR-008 explicitly requires a repo-wide verification step, delivered as a
committed static test (`tests/static/test_no_old_package_name.py`) rather than a one-off manual
check (research.md #4), plus the pre-existing suite re-run under the new name (FR-005).

**Organization**: Tasks are grouped by user story (US1 = install/import under the new name, P1;
US2 = no stale references anywhere, P2; US3 = rename documented in CHANGELOG, P3) per spec.md
priorities, on top of a shared Foundational phase — all three stories depend on the same core
rename (directory move, `pyproject.toml` identifiers, internal imports) existing first, since a
half-renamed package doesn't import, build, or test at all.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow plan.md's Project Structure and data-model.md's Reference site categories

---

## Phase 1: Setup

**Purpose**: Establish a baseline and a failing verification test before touching any code, so
progress is measurable against a known starting point.

- [X] T001 Confirm the working tree is on branch `012-rename-package-mfgparams`; run
  `grep -rl "machine_calc\|machine-calc" --include="*.py" --include="*.toml" --include="*.md" --include="*.yml" --include="*.rst"`
  scoped to `src/ tests/ docs/ scripts/ .github/ pyproject.toml README.md CHANGELOG.md` (i.e.
  excluding `specs/001-011` history and gitignored build output) and record the file count as
  the before-snapshot referenced in research.md's Scale/Scope (no file edit)
- [X] T002 [P] Write `tests/static/test_no_old_package_name.py`: walk tracked files under the
  same scope as T001, assert zero occurrences of `machine_calc`/`machine-calc`, with allowances
  for exactly the three exclusions in data-model.md's Exclusion rule — (1) any
  `github.com/kniklas/machine-calc` URL, (2) `specs/001-*` through `specs/011-*` plus this
  feature's own `specs/012-rename-package-mfgparams/**` and pre-existing `CHANGELOG.md`
  entries/`tests/contract/data/README.md`'s historical fixture-provenance note, (3) gitignored
  paths (`*.egg-info/`, `build/`, `dist/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`).
  Expected to **FAIL** at this point — that failure is the acceptance signal the later tasks
  clear (FR-008; research.md #4)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The core rename every user story depends on: the package directory, its packaging
metadata, its own internal imports, and the CI tool configs that point at it by path. Until this
lands, the package doesn't install, import, or test successfully at all.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 `git mv src/machine_calc src/mfgparams` (research.md #2) — preserves file history for
  the moved directory
- [X] T004 Update `pyproject.toml`: `[project].name = "mfgparams"`,
  `[project.scripts]` (`mfgparams = "mfgparams.__main__:main"`, replacing the
  `machine-calc = "machine_calc.__main__:main"` entry — research.md #5, no alias kept per
  FR-006), `[tool.setuptools.dynamic].version` → `{ attr = "mfgparams.__version__" }`,
  `[tool.setuptools.package-data]`'s `machine_calc = [...]` key → `mfgparams = [...]`,
  `[tool.pytest.ini_options].addopts`'s `--cov=machine_calc` → `--cov=mfgparams`,
  `[tool.coverage.run].source`'s `["machine_calc"]` → `["mfgparams"]`, `[tool.mypy].files`'s
  `["src/machine_calc"]` → `["src/mfgparams"]` (data-model.md Identifiers table; depends on T003)
- [X] T005 [P] Update every internal reference within `src/mfgparams/**/*` — not just imports —
  to `mfgparams`. This covers: (a) the 18 files with absolute `from machine_calc import ...` /
  `import machine_calc` statements and their docstrings (`__init__.py`, `__main__.py`, `cli.py`,
  `units.py`, `registry.py`, `validation.py`, and `operations/{drilling,milling}/**`); (b)
  load-bearing **dynamic/string-literal** package-path references that a plain import-statement
  fix would miss: `i18n.py`'s `importlib.import_module(f"machine_calc.locales.{locale}")` (line
  49), and the four `_BUNDLED_PACKAGE = "machine_calc...."` constants in `registry.py:28`,
  `operations/drilling/tools.py:24`, `operations/milling/end_milling/tools.py:23`,
  `operations/milling/face_milling/tools.py:18` — all passed to `importlib.resources`-based
  loaders, so leaving them stale breaks bundled material/tool-data loading at runtime, not just
  cosmetically; (c) the three `.toml` data files with `` `machine_calc.registry` `` comment
  references: `operations/drilling/data/tools.toml`,
  `operations/milling/end_milling/data/tools.toml`,
  `operations/milling/face_milling/data/tools.toml`. Also change `cli.py`'s
  `argparse.ArgumentParser(prog="machine-calc")` to `prog="mfgparams"` so `--help` output shows
  the new command name (depends on T003)
- [X] T006 [P] Update `.github/workflows/ci.yml`'s hard-coded package-path targets: the `mypy`
  step's `src/machine_calc` → `src/mfgparams`, and the `pytest --cov=machine_calc ...` step →
  `--cov=mfgparams` (depends on T003)
- [X] T007 Rename all three `MACHINE_CALC_*` environment variables to their `MFGPARAMS_*`
  equivalents, project-wide:
  - `MACHINE_CALC_LOCALE` → `MFGPARAMS_LOCALE`: declaration in `src/mfgparams/i18n.py`
    (`_LOCALE_ENV_VAR`, plus doc references at lines ~5, 66, 82); doc mentions in
    `src/mfgparams/cli.py` (lines ~10, 127, 558, 1076); `README.md:228`; and every test that
    sets/reads it — `tests/unit/shared/test_i18n.py`,
    `tests/contract/test_library_api_milling_locale.py`, `tests/integration/test_locale_env.py`,
    `tests/integration/test_cli_materials_config.py`, `tests/integration/test_cli_material_types.py`.
  - `MACHINE_CALC_RUN_PERFORMANCE_TESTS` → `MFGPARAMS_RUN_PERFORMANCE_TESTS`:
    `tests/performance/conftest.py` (declaration + skip-gate logic, lines ~7, 26, 36);
    `.github/workflows/ci.yml`'s performance job invocation (~line 238); `README.md:267`;
    `tests/performance/test_harness_subprocess_boundary.py`,
    `tests/performance/test_calculation_budgets.py`,
    `tests/unit/performance/test_harness_memory_validation.py`.
  - `MACHINE_CALC_PERFORMANCE_SUMMARY_PATH` → `MFGPARAMS_PERFORMANCE_SUMMARY_PATH`:
    `.github/workflows/ci.yml`'s `env:` declaration (~line 230) and
    `os.environ[...]` read (~line 265); `tests/performance/results.py`'s
    `SUMMARY_PATH_ENV_VAR` constant (line 26).

  (research.md #7, extended per /speckit-analyze finding E1; depends on T005, T006 — it touches
  `src/mfgparams/i18n.py`/`cli.py` which T005 also edits, and `.github/workflows/ci.yml` which
  T006 also edits, so it runs after both to avoid overlapping-file conflicts, not because of a
  real logical dependency between them)
- [X] T008 Update every test file's references to the old name across
  `tests/{unit,contract,integration,static,performance,scripts}/**/*.py` (~80 files) — not just
  `from machine_calc import ...` / `import machine_calc` statements, but every functional
  occurrence, including: hard-coded paths (`tests/contract/test_cli_contract.py`'s
  `Path(__file__).resolve().parents[2] / "src" / "machine_calc" / "cli.py"`),
  `importlib.metadata.version("machine-calc")` (`tests/unit/test_version_single_source.py`),
  `monkeypatch.setattr(sys, "argv", ["machine-calc"])`
  (`tests/integration/test_cli_edge_cases.py`), module-name-prefix-derivation logic
  (`tests/contract/test_library_api_milling.py:160-188`), and the string-literal assertion in
  `tests/static/test_no_hardcoded_strings.py:48` (`"machine_calc.i18n" not in source`) —
  updating it to `"mfgparams.i18n"` so the check keeps testing a real invariant instead of
  passing vacuously. Leave `tests/contract/data/README.md` and pre-existing `CHANGELOG.md`
  entries untouched (historical record, not a stray reference) (depends on T007 — T007's env-var
  renames already touch several of these same test files, e.g. `conftest.py`, `results.py`,
  `test_i18n.py`, `test_locale_env.py`; running after it avoids overlapping-file conflicts)
- [X] T009 Remove stale generated artifacts so they regenerate under the new name:
  `src/machine_calc.egg-info/`, `build/`, `dist/`, `.mypy_cache/`, `.ruff_cache/`,
  `.pytest_cache/`; then run `pip install -e ".[dev]"` and confirm a fresh
  `src/mfgparams.egg-info/` is created (research.md #2 exclusion item 2; depends on T003, T004)

**Checkpoint**: The package installs and imports under `mfgparams`; CI tool configs point at the
right paths. Documentation (US2) and the CHANGELOG entry (US3) are still pending.

---

## Phase 3: User Story 1 - Install and import under the new, generic name (Priority: P1) 🎯 MVP

**Goal**: Anyone installing or importing the library gets it under the short, generic
`mfgparams` name, with identical CLI/library behavior to before the rename, and the old name is
no longer available at all (spec.md User Story 1; FR-001, FR-002, FR-004, FR-006).

**Independent Test**: Install into a clean virtual environment, `import mfgparams`, run the CLI
end-to-end, and confirm neither `machine-calc` nor `machine_calc` is installable/importable
anymore (quickstart.md steps 1-2).

- [X] T010 [US1] Run quickstart.md steps 1-2 in a clean virtual environment: fresh
  `pip install -e ".[dev]"`, `python -c "import mfgparams; print(mfgparams.__version__)"`,
  `mfgparams --help`, then one full interactive CLI calculation flow (e.g. a drilling
  calculation), and confirm the output matches pre-rename `machine-calc` behavior exactly
  (contract G2/G3/G4; depends on T003-T009)
- [X] T011 [US1] Confirm the old identity is fully gone: `python -c "import machine_calc"`
  raises `ModuleNotFoundError`, and no `machine-calc` console script remains on `PATH` after
  install (spec.md User Story 1 Acceptance Scenario 3; contract G1; depends on T003, T004, T009)
- [X] T012 [US1] Run the full automated test suite (`pytest`) and confirm 100% of it passes with
  no drop in coverage (FR-005; depends on T003-T009)

**Checkpoint**: User Story 1 is independently functional and testable — the package works
end-to-end under its new name, with no trace of the old one left installed.

---

## Phase 4: User Story 2 - No stale references anywhere in the project (Priority: P2)

**Goal**: Every functional reference to the old name — in docs, scripts, CI comments, and
hand-authored skill docs — is updated, so no maintainer or contributor hits a stale reference
(spec.md User Story 2; FR-003, FR-008).

**Independent Test**: Run the static verification test and the full suite; both come back clean
independent of User Story 1 (quickstart.md step 3; spec.md Acceptance Scenarios).

- [X] T013 [US2] Update `README.md`: the `# machine-calc` title, the free-for-noncommercial-use
  prose line, the Sphinx-docs link text, the `from machine_calc import ...` code examples, the
  `python -m machine_calc` invocation examples, the `machine-calc --materials-config ...` CLI
  example, and the example filename `my-machine-calc.toml` → `my-mfgparams.toml`. Do **not**
  touch the CI/codecov badge URLs or the GitHub Pages link
  (`https://kniklas.github.io/machine-calc/`) — those key off the unchanged repository slug
  (data-model.md Exclusion rule; depends on T003-T009 so the examples reflect real behavior)
- [X] T014 [P] [US2] Update `docs/source/conf.py` (`project = "machine-calc"` and its module
  docstring) and every `docs/source/*.rst` file's prose plus `automodule::`/`:class:`/`:func:`/
  `:mod:` autodoc directives (`index.rst`, `milling.rst`, `drilling.rst`, `drilling-api.rst`,
  `milling-api.rst`) from `machine_calc.*` to `mfgparams.*` (research.md #6; depends on T005)
- [X] T015 [P] [US2] Update `scripts/sync_agent_integrations.py`'s header comment ("Not part of
  the machine_calc package...") to reference `mfgparams`
- [X] T016 [P] [US2] Update the hand-authored skill docs that mention the old name —
  `.github/skills/pypi-package-builder/SKILL.md`, `.github/skills/pr-review-loop/SKILL.md`,
  `.github/skills/code-review/SKILL.md`, `.github/skills/skill-authoring/SKILL.md` — per
  Constitution Principle XI's explicit hand-authored-skill exception. Do **not** touch any
  generated per-agent file (`.github/agents/*.agent.md`, `.github/prompts/*.prompt.md`,
  `.claude/skills/speckit-*`) — verified in plan.md to contain no project-specific package name,
  and hand-patching them is forbidden regardless (Principle XI)
- [X] T017 [US2] Run `tests/static/test_no_old_package_name.py` (from T002) and confirm it now
  **PASSES**; fix any remaining stray reference it surfaces before proceeding (FR-008, SC-001;
  depends on T004, T005, T006, T007, T008, T013, T014, T015, T016)
- [X] T018 [US2] Spot-check the intentionally-excluded references are still intact:
  `grep -n "kniklas/machine-calc" README.md LICENSE.md` still finds the CI/codecov badge URLs
  and the license notice/issue-link line, unchanged (quickstart.md step 7; depends on T013)

**Checkpoint**: User Stories 1 and 2 are both independently functional — the rename works
end-to-end (US1) and leaves no stale reference behind in anything this feature is scoped to
touch (US2).

---

## Phase 5: User Story 3 - Rename is documented for future readers (Priority: P3)

**Goal**: The project's change history records that the package was renamed, from what, and why
(spec.md User Story 3; FR-007).

**Independent Test**: Read `CHANGELOG.md` after the rename ships and confirm it documents the
change (quickstart.md; spec.md Acceptance Scenario).

- [X] T019 [US3] Add a new `CHANGELOG.md` entry documenting the rename from
  `machine-calc`/`machine_calc` to `mfgparams`, stating the reason (a shorter, more generic name
  reflecting the library's multi-material scope, issue #62) and noting the console-script and
  import-path change consumers must make. Leave the pre-existing entries at lines 117 and 140
  (which reference `machine_calc.__version__` / `machine_calc.registry...` as historical fact
  about past releases) unchanged — they describe what was true when written, per FR-007's own
  "record the rename" framing, not what to retroactively rewrite (depends on T003-T018 so the
  entry accurately describes the final, shipped state)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final gates spanning all three user stories, plus the one reference this feature
deliberately routes through a separate process rather than a direct edit.

- [X] T020 [P] Build distributables (`python -m build`) and confirm every artifact under
  `dist/` is named `mfgparams-*`, with none named `machine_calc-*`/`machine-calc-*` (SC-004;
  quickstart.md step 5)
- [X] T021 [P] Build Sphinx docs locally
  (`sphinx-build -b html docs/source docs/_build/html`) and confirm no autodoc import errors
  (Constitution Principle VII; quickstart.md step 6; depends on T014)
- [X] T022 Run the full local CI-equivalent gate set (`ruff`, `black --check`, `mypy`,
  `radon`/`xenon` via `scripts/check_maintainability.py`, `bandit`) against `src/mfgparams` and
  confirm all pass, validating that T004/T006's config repointing didn't silently narrow or
  break any Principle IX gate (depends on T003-T009)
- [X] T023 Final full-repo sweep: re-run T001's grep across the same scope and confirm the only
  remaining hits are the documented exclusions (data-model.md Exclusion rule) — catches anything
  the categorized tasks above missed (depends on T004-T019)
- [X] T024 File a follow-up to update `.specify/memory/constitution.md`'s three prose mentions
  of `machine-calc` (the title `# machine-calc Constitution` and the Principle IV/V rationale
  sentences) via `/speckit-constitution`, **not** a direct edit here — the constitution's own
  Governance section requires a documented rationale and version bump for any change to it,
  which is `/speckit-constitution`'s job, not a task this feature's implementation should
  perform as a side effect

**Checkpoint**: Rename complete, verified, documented, and built cleanly; the one governance
document in scope is explicitly handed off rather than silently edited.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately. T002 (failing static test) can be
  written in parallel with T001 (a read-only baseline check).
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all three user stories (none
  of them can be verified against a package that doesn't yet install/import under the new name).
- **User Story 1 (Phase 3)**, **User Story 2 (Phase 4)**, **User Story 3 (Phase 5)**: All depend
  only on Foundational completion. US3's CHANGELOG entry additionally waits on US1/US2 so it
  accurately describes the finished state, rather than being a strict code dependency.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2). No dependency on US2 or US3.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2), independently of US1 — it
  touches docs/scripts/skills, not the install/import path US1 verifies.
- **User Story 3 (P3)**: Written last by convention (so the entry is accurate), but has no
  structural code dependency on US1/US2 completing first.

### Within Each Phase

- Foundational: T003 (directory move) before T004-T009 (everything else references the new
  path). T005 and T006 touch disjoint file sets (`src/mfgparams/**` vs `.github/workflows/ci.yml`)
  and can run in parallel once T003 lands. T007's env-var renames overlap both — `i18n.py`/
  `cli.py` with T005, `ci.yml` with T006 — so it runs after them, sequentially. T008 overlaps
  T007's test-file edits (`conftest.py`, `results.py`, `test_i18n.py`, `test_locale_env.py`,
  etc.), so it runs after T007, sequentially.
- User Story 2: T014, T015, T016 touch disjoint files and can run in parallel; T017 (verification
  test) must run last, after every content task in this phase.

### Parallel Opportunities

- T001 and T002 in Setup (read-only check vs. new test file).
- T005 and T006 in Foundational (disjoint file sets: `src/mfgparams/**` vs
  `.github/workflows/ci.yml`). T007 and T008 are sequential, not parallel — both overlap
  files T005/T006/T007 already touch (see Within Each Phase above).
- T014, T015, T016 in User Story 2 (disjoint files: `docs/source/**`,
  `scripts/sync_agent_integrations.py`, `.github/skills/**`).
- T020, T021 in Polish (build vs. docs build).

---

## Parallel Example: Foundational sweep

```bash
# Once T003 (git mv) lands, these two can run together:
Task: "Update internal imports/docstrings in src/mfgparams/**/*.py (T005)"
Task: "Repoint CI tool-config targets in .github/workflows/ci.yml (T006)"

# T007 (env-var renames) then runs after both land, since it touches files each
# of them already edited; T008 (test-file sweep) then runs after T007 for the
# same reason.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run quickstart.md steps 1-2; confirm SC-002/SC-003
5. The package is installable and usable under its new name — US2/US3 add reference-hygiene
   and documentation polish on top

### Incremental Delivery

1. Complete Setup + Foundational → package renamed and installable
2. Add User Story 1 (install/import/CLI parity) → test independently → this is the shippable
   core of issue #62
3. Add User Story 2 (no stale references) → test independently via the static check
4. Add User Story 3 (CHANGELOG entry) → done
5. Polish (build/docs verification, full gate re-run, constitution follow-up) → merge as one
   atomic PR (plan.md Structure Decision — no long-lived integration branch for this feature)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit as one atomic PR to `main` per plan.md's Structure Decision — do not merge a
  partially-renamed intermediate state, since every merge to `main` triggers a PyPI release
- Explicitly out of scope for every task above (per spec.md Clarifications): the GitHub
  repository/local clone directory rename, and the `my-project/` scaffold directory (tracked in
  issue #67)
- Explicitly left unedited by design (historical record, not stale references): `CHANGELOG.md`
  lines 117/140, `tests/contract/data/README.md`'s fixture-provenance note, and every
  `specs/001-*` through `specs/011-*` feature document
