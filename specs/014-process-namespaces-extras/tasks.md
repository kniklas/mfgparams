---

description: "Task list for feature implementation"
---

# Tasks: Process Namespaces and Installation Extras

**Input**: Design documents from `/specs/014-process-namespaces-extras/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Test tasks ARE included. Constitution Principle II is NON-NEGOTIABLE, and four requirements (FR-008, FR-011, FR-015, FR-017) explicitly demand automated enforcement rather than convention.

**Organization**: Grouped by user story so each is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1, US2, US3 — maps to the user stories in spec.md
- Exact file paths are given in every task

## Path Conventions

Single project, `src/` layout: `src/mfgparams/`, `tests/` at repository root (see plan.md → Project Structure).

## Traceability note

FR-015 (bundled data in the built artifact) spans two stories by design: the `package-data` metadata
update lands in US1 with the move that invalidates it (T014), while the build-and-inspect assertions
land in US3 (T036) where spec.md places them. Neither story is complete without its half.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the pre-move baseline that FR-003 ("no calculation result changes") is verified against. Without this, "identical results" is unfalsifiable after the move.

- [X] T001 Capture the pre-move baseline in `specs/014-process-namespaces-extras/baseline.md`: full `pytest` pass/skip counts, the coverage percentage, and the computed output of one drilling, one end-milling and one face-milling calculation at fixed inputs
- [X] T002 [P] Confirm the unmodified tree is green before any change: `pip install -e ".[dev]"`, then `tox` and `tox -e packaging` both pass

**Checkpoint**: A recorded baseline exists to compare against.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the destination package skeletons both moves target.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create `src/mfgparams/processes/__init__.py` with a docstring naming the process→operation grouping and the deferred processes (turning, welding, joining, forming), **and create the `src/mfgparams/processes/machining/` directory itself** — `git mv` into a destination whose parent does not exist fails outright (`fatal: renaming ... failed: No such file or directory`, exit 128), so T005 and T006 cannot run until it is there. Its `__init__.py` still lands in T007, with the docstring carried over from the old `operations/__init__.py`.
- [X] T004 [P] Create `src/mfgparams/console/__init__.py` with a docstring stating that the console is presentation-only and that core must never import it (FR-008)

**Checkpoint**: Destination packages exist; US1 and US2 can proceed in parallel.

---

## Phase 3: User Story 1 - Reach a calculation by process and operation (Priority: P1) 🎯 MVP

**Goal**: Calculations are reachable at `mfgparams.processes.machining.*`, the old `mfgparams.operations.*` paths are gone with no alias, and every result is bit-identical to the baseline.

**Independent Test**: Import drilling, end-milling and face-milling through their process-qualified paths in a fresh environment, compute results, and confirm they match `baseline.md`; confirm `mfgparams.operations` raises `ModuleNotFoundError`.

### Move (one commit, no content edits beyond imports — research.md #6)

- [X] T005 [US1] `git mv src/mfgparams/operations/drilling src/mfgparams/processes/machining/drilling`
- [X] T006 [US1] `git mv src/mfgparams/operations/milling src/mfgparams/processes/machining/milling`
- [X] T007 [US1] Create `src/mfgparams/processes/machining/__init__.py`, rewriting the registry docstring from the old `src/mfgparams/operations/__init__.py` so it describes the process-first grouping (the one file whose content legitimately changes — data-model.md footnote 1)
- [X] T008 [US1] Delete the now-empty `src/mfgparams/operations/` directory and confirm `git status` shows the moves as renames, not add/delete pairs

### Import rewrites

- [X] T009 [US1] Rewrite intra-package imports in `src/mfgparams/processes/machining/drilling/{__init__,formulas,tools}.py`
- [X] T010 [US1] Rewrite intra-package imports in `src/mfgparams/processes/machining/milling/{__init__,_shared,_calculate,_tool_registry}.py`
- [X] T011 [US1] Rewrite intra-package imports in `src/mfgparams/processes/machining/milling/{end_milling,face_milling}/{__init__,formulas,tools}.py`
- [X] T012 [US1] Update the four operation imports in `src/mfgparams/__init__.py` (lines 37-43) **and the module docstring** (line 22 names `mfgparams.operations.<operation>`; lines 18-20 and 24 name `operations.drilling` and `operations.milling.*` without the package prefix, so T037 will not flag them but they teach the wrong path), keeping `__all__` byte-identical (FR-005)
- [X] T013 [US1] Update the four operation imports in `src/mfgparams/cli.py` (lines importing `operations.drilling.tools`, `operations.milling._tool_registry`, and both milling sub-operation tool modules)
- [X] T013a [US1] Update the old-layout references in the docstrings of the two **unmoved** core modules: `src/mfgparams/models.py` (lines 3, 58, 76) and `src/mfgparams/registry_config.py` (line 7). data-model.md correctly lists both under *Unmoved*, so no move task touches them — but T037's FR-017 check scans the *content* of every tracked file, so leaving them fails T037 and T041 at the end of the run.
- [X] T014 [US1] Update the **three** `operations/**/data/*.toml` globs in `[tool.setuptools.package-data]` in `pyproject.toml` to their `processes/machining/**` paths. The fourth entry, `data/*.toml`, is core `materials.toml` and does not move — the original "four" miscounted it as relocating.

### Test import rewrites

- [X] T015 [P] [US1] Rewrite `mfgparams.operations` imports across `tests/contract/`
- [X] T016 [P] [US1] Rewrite `mfgparams.operations` imports across `tests/integration/`
- [X] T017 [P] [US1] Rewrite `mfgparams.operations` imports across `tests/unit/` and `tests/performance/`

### Tests for User Story 1

- [X] T018 [US1] Extend the public-surface test in `tests/contract/test_library_api_milling.py` from the two milling entry points to all 14 names in `mfgparams.__all__`, asserting each is present, exported and of the expected kind (FR-005)
- [X] T019 [P] [US1] Add a test asserting `importlib.import_module("mfgparams.operations")` raises `ModuleNotFoundError`, in `tests/contract/test_library_api_milling.py` or a sibling (FR-004)
- [X] T020 [US1] Verify FR-003: re-run `pytest tests/contract tests/integration` and diff pass/skip counts and the three golden calculations against `baseline.md`

**Checkpoint**: Process-qualified paths work, old paths are gone, results are provably unchanged. This alone is a coherent, releasable increment.

---

## Phase 4: User Story 2 - Install only what is needed (Priority: P1)

**Goal**: The console lives in `mfgparams.console` behind a declared extra, a default install carries no console dependencies, core never imports the console, and invoking the console without its dependencies gives an actionable message instead of a traceback.

**Independent Test**: Install without extras into a clean venv, confirm the calculation API works and only `mfgparams` (plus `tomli` below 3.11) is installed; then confirm both console invocation forms behave identically to before.

### Move and entry points

- [X] T021 [US2] `git mv src/mfgparams/cli.py src/mfgparams/console/cli.py`
- [X] T022 [US2] Create `src/mfgparams/console/__main__.py` delegating to `mfgparams.__main__.main` — **delivered differently from as written**: it first delegated to `mfgparams.console.cli.main`, which made `python -m mfgparams.console` the one invocation form that bypassed the FR-011 guard and answered a missing dependency with a traceback. Copilot review banded that HIGH; FR-011 is unqualified, and this is a form a user reaches by guessing. It now routes through the guarded entry point like the other two, `console/cli.py`'s own `if __name__ == "__main__"` block is gone (it was an unguarded *fourth* form), and `tests/static/test_entry_points_are_guarded.py` fails if a new runnable module appears
- [X] T023 [US2] Rewrite `src/mfgparams/__main__.py` to define its own `main()` that imports the console **inside the function body**, wrapped in the FR-011 guard exactly as specified in contracts/console-entry-contract.md § *What the guard actually wraps* — the `try` encloses the lazy console import, and any `ModuleNotFoundError` whose `exc.name` roots at `mfgparams` is re-raised rather than reported as a missing extra — **delivered broader than as written**, in three ways review established were required by FR-011 rather than optional: (a) the guard also wraps the console's *execution*, because #63 permits a dependency to be imported lazily inside the call, where an import-only guard emits the traceback FR-011 forbids; (b) "roots at `mfgparams`" became `_is_broken_core`, which also re-raises for a *core runtime requirement* read from installed metadata, since a user cannot fix a missing `tomli` by installing `mfgparams[console]`; (c) the execution-time half cannot ask what is missing — an import name is not a distribution name — so it asks *who imported it*, by frame provenance. The non-integer console status and the console package's import-free `__init__.py` are part of the same contract. All of it is specified in contracts/console-entry-contract.md
- [X] T024 [US2] Confirm `[project.scripts] mfgparams = "mfgparams.__main__:main"` still resolves after T023, since `__main__.py` now defines `main` rather than re-exporting it

### Packaging and messages

- [X] T025 [P] [US2] Add `console = []` and `all = ["mfgparams[console]"]` to `[project.optional-dependencies]` in `pyproject.toml`, with a comment recording why the extra is declared while empty (contracts/installation-extras-contract.md). `all` is a **self-referential extra**, which pip only resolves from 21.2 onward; that is now a load-bearing floor rather than an incidental one, so keep the README's existing `python -m pip install --upgrade pip` step (README line 37, currently justified by PEP 660) and record the second reason beside it.
- [X] T026 [P] [US2] Add the missing-console message to `src/mfgparams/locales/en.py` under a stable ID, with a comment stating it MUST stay in the core catalogue when slice 015 relocates the others (research.md #4)
- [X] T027 [P] [US2] Rewrite `mfgparams.cli` imports across `tests/` to `mfgparams.console.cli`

### Tests for User Story 2

- [X] T028 [P] [US2] Add `tests/static/test_core_does_not_import_console.py`: parse every module under `src/mfgparams/` except `__main__.py` with `ast` and fail on any import naming `mfgparams.console` (FR-008)
- [X] T029 [P] [US2] Add a runtime assertion to the same file that importing `mfgparams` and each `processes.machining.*` module leaves `mfgparams.console` absent from `sys.modules` — this is what keeps `__main__.py`'s exemption honest (FR-008)
- [X] T030 [P] [US2] Add a test named `test_console_missing_dependency_*` asserting the guard emits one actionable message naming the install command on stderr, exits non-zero, and raises no traceback. **The command is delivered as `<sys.executable> -m pip install "mfgparams[console]"`** rather than the bare `pip install mfgparams[console]` written here: review established the bare form is not runnable, since zsh globs `[console]` and aborts before pip runs, and a bare `pip` on a multi-Python machine installs into the wrong interpreter and reproduces this same message. Simulate the failure by making a non-`mfgparams` module the console imports unresolvable (e.g. `monkeypatch.setitem(sys.modules, "<dep>", None)`), never by patching the guard itself. Add the companion case too: a `ModuleNotFoundError` naming an `mfgparams.*` module must propagate, not be swallowed (FR-011)
- [X] T031 [US2] Add a `packaging`-marked test asserting a default (no-extras) install resolves no console-only dependency (FR-009, FR-013)
- [X] T032 [US2] Verify FR-012 manually per quickstart.md §5: `mfgparams --help` and `python -m mfgparams --help` produce identical output and exit 0

**Checkpoint**: Both P1 stories complete. The package is structurally what issue #63 part 1 asked for.

---

## Phase 5: User Story 3 - Find the code and the docs where the structure says they are (Priority: P2)

**Goal**: Tests, docs and packaging metadata mirror the new structure, and the old layout cannot be reintroduced.

**Independent Test**: Search the repository for old-layout references and find none outside the documented exclusions; build the distribution and confirm every bundled data file is at its new path.

- [X] T033 [P] [US3] `mkdir -p tests/unit/processes` **first** (the `git mv` fails without it, as in T003), then `git mv tests/unit/operations tests/unit/processes/machining`. Add `tests/unit/processes/__init__.py` only if the existing partial markers require it — today only `tests/unit/operations/milling/` and its two sub-operation directories carry one; `tests/unit/`, `tests/unit/operations/` and `tests/unit/operations/drilling/` do not. (FR-014)
- [X] T034 [P] [US3] Update **both** old-path references in `docs/source/drilling-api.rst` — the prose at line 5 and the directory-tree block at line 133 — to `mfgparams.processes.machining.drilling` / `mfgparams/processes/machining/drilling/` (FR-016)
- [X] T035 [P] [US3] Update **both** old-path references in `docs/source/milling-api.rst` — the prose at line 5 and the directory-tree block at line 128 — to `mfgparams.processes.machining.milling` / `mfgparams/processes/machining/milling/` (FR-016)
- [X] T036 [US3] Extend `tests/integration/test_packaging_bundled_data.py` to assert all four `.toml` files are present at their new paths in the built wheel **and** that no `.toml` remains under any `mfgparams/operations/` path (FR-015). Tighten the existing assertions (lines 146-149) from suffix matches such as `endswith("drilling/data/tools.toml")` to the full in-wheel path: those suffixes are unchanged by the move, so as written they keep passing even if `[tool.setuptools.package-data]` is never updated - which is precisely the silent failure this test exists to catch.
- [X] T037 [US3] Add `tests/static/test_no_old_layout.py` modelled on `tests/static/test_no_old_package_name.py`: scan every git-tracked file's content *and its tracked path* for `mfgparams.operations` / `mfgparams/operations`, excluding prior specs, `specs/014-*/`, the constitution, `CHANGELOG.md`, and the check's own source (FR-017, research.md #5)
- [X] T038 [P] [US3] Give the README an end-user install section with the three commands (`pip install mfgparams`, `"mfgparams[console]"`, `"mfgparams[all]"`) and a package-structure block showing the process-qualified paths (FR-016). This *adds* content rather than correcting stale paths: the README had no structure section and no `mfgparams.operations` reference at all, only `## Install (development)`. The original wording named two sections that did not exist.

**Checkpoint**: All three stories complete; nothing points at the old layout.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T039 Add the `## [Unreleased]` CHANGELOG entry describing the restructure as breaking, explicitly noting no version bump is cut by this feature (FR-018)
- [X] T040 Run every section of [quickstart.md](./quickstart.md) end to end and fix any drift between it and the delivered code
- [X] T041 Run the full gate set, each invocation copied verbatim from `.github/workflows/ci.yml` so a local run and CI measure the same thing:
  - `tox` (py39–py312) and `tox -e packaging`
  - `ruff check src/ tests/ scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py`
  - `black --check src/ tests/ scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py`
  - `mypy src/mfgparams scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py`
  - `python scripts/check_maintainability.py src/ scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py`
  - `bandit -r src scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py -ll`
  - `pip-audit`
  - `python scripts/setup_skill_symlinks.py --check`
  - `sphinx-build -b html docs/source docs/_build/html -W` — this feature edits both Sphinx pages, and `-W` turns any warning into a failure

  The original list claimed CI parity it did not have: `ruff check .` and `black --check .` scan a wider tree than CI does, bare `mypy` a narrower one, and `pip-audit`, the docs build and the skill-symlink check were missing outright.
- [X] T042 Confirm coverage is at or above 90% and update the README coverage badge/number if it moved (Principle VII, SC-006)
- [X] T043 Self-review the diff against the Development Workflow checklist in `.specify/memory/constitution.md` — in particular that the move commits contain no content edits beyond import lines
- [X] T044 Cross-checked spec, plan and tasks before opening the pull request. `/speckit-analyze` ran in full **before** implementation (2026-08-31) and its blocking findings were applied; the post-implementation pass was the same cross-check run against the delivered tree, not a second skill invocation. Note for the reviewer: `/speckit-converge` is the check that belongs at this point in the list — analyze only compares the three artifacts to each other and cannot detect implementation work that never happened (constitution, Principle XII).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies. T001 MUST complete before any file moves — the baseline is worthless if captured after the change.
- **Foundational (Phase 2)**: Depends on Setup. Blocks both P1 stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on Phase 2. Independent of US1 — see below.
- **User Story 3 (Phase 5)**: Depends on US1 and US2, since it mirrors and verifies what they produce.
- **Polish (Phase 6)**: Depends on all three stories.

### User Story Independence

- **US1 and US2 are genuinely independent and may be done in either order.** Their only contact point is `cli.py`, which US1 edits (T013) and US2 moves (T021). Whichever runs second inherits the other's result; neither blocks the other. If both are worked in parallel, sequence T013 before T021 to avoid editing a file mid-move.
- **US3 depends on both** by nature — it verifies and mirrors.

### Within Each User Story

- Moves before import rewrites; import rewrites before tests.
- T020 and T032 are verification gates: do not close the story with them failing.

### Parallel Opportunities

- T015, T016, T017 touch disjoint test directories — fully parallel.
- T025, T026, T027 touch `pyproject.toml`, `locales/en.py` and `tests/` respectively — fully parallel.
- T028, T029, T030 are new independent test files/cases — parallel, though T029 belongs in the same file as T028.
- T033, T034, T035, T038 touch disjoint files — fully parallel.

---

## Parallel Example: User Story 1 test rewrites

```bash
Task: "Rewrite mfgparams.operations imports across tests/contract/"
Task: "Rewrite mfgparams.operations imports across tests/integration/"
Task: "Rewrite mfgparams.operations imports across tests/unit/ and tests/performance/"
```

## Parallel Example: User Story 2 packaging and messages

```bash
Task: "Add console/all extras to pyproject.toml"
Task: "Add the missing-console message to src/mfgparams/locales/en.py"
Task: "Rewrite mfgparams.cli imports across tests/"
```

---

## Implementation Strategy

### Commit shape (research.md #6)

Keep the mechanical moves in commits containing **only** moves and the import rewrites they force
(T005–T017, T021, T027, T033). Everything behavioural — the FR-011 guard, the new tests, packaging
metadata, docs — lands in separate commits on top. Git's rename detection only holds when a moved
file's contents are near-unchanged, so mixing a behavioural edit into a move commit turns a
reviewable `R100` into an add/delete pair and hides the real change. This split is also what lets a
reviewer confirm FR-003 by inspection.

### MVP scope

**User Story 1 alone** is the MVP: it delivers the process-first namespace that issue #63 part 1 is
fundamentally about, and it is releasable on its own. In practice both P1 stories should land in the
same pull request, since shipping the namespace move without the console split would mean two
breaking restructures in a row for no gain.

### Incremental delivery

1. Setup + Foundational → destinations exist, baseline recorded
2. US1 → process paths work, results provably unchanged → **checkpoint**
3. US2 → console separated, extras declared, layering enforced → **checkpoint**
4. US3 → mirrored and guarded against regression
5. Polish → gates green, changelog written, ready for review

---

## Notes

- `[P]` tasks touch different files and have no incomplete dependencies.
- This feature cuts **no release** (FR-018); changes accumulate under `## [Unreleased]` toward a single 2.0.0 once slices 015–017 land and before issue #40 publishes.
- Do not add a compatibility alias for `mfgparams.operations` at any point, even temporarily — FR-004 forbids it and T037 will fail on it.

---

## Phase 7: Convergence

Appended by `/speckit-converge` on 2026-08-31, after Phases 1-6 completed. Each item traces
to the artifact obligation it closes. The common cause: plan.md's Constitution Check recorded
"XI. Multi-Agent Consistency - No skill or agent-integration file changes. PASS", but FR-017
reaches *every* tracked file, and two files under `.github/skills/` still describe the
operation-first layout.

- [X] T045 Repoint the two stale layout paths in `.github/skills/code-review/SKILL.md` — `operations/*/formulas.py` (line 186) and `operations/<name>/` (line 281) — at `processes/<process>/<operation>/`, per FR-017, SC-004 and US1 acceptance scenario 4 (partial). Highest-value of the four: this file is what GitHub Copilot reads to review this repository, so the stale paths do not merely document the wrong location, they send an automated reviewer to a directory that no longer exists. Leave line 175's `new operations/units` alone — that is prose, not a path.
- [X] T046 Correct `.github/skills/pypi-package-builder/SKILL.md:100`, which documents `[project.scripts] mfgparams = "mfgparams.cli:main"`, per FR-007 and FR-012 (contradicts). `mfgparams.cli` no longer exists, and the real entry point is and was `mfgparams.__main__:main` — this example was already wrong before this feature and the console move makes it doubly so, so fix it to match `pyproject.toml` rather than merely re-pathing it to `mfgparams.console.cli:main`.
- [X] T047 Widen `tests/static/test_no_old_layout.py`'s pattern so FR-017's "enforced automatically" clause actually covers the form T045 and T046 are examples of (partial). Today it matches only `mfgparams[./]operations`; the bare `operations/<segment>/` path form slips through, which is why those two files survived Phase 5. Verified against the tree: `operations/[^ ]*/` matches all four real occurrences and does **not** match the prose `new operations/units`. Adding it requires excluding `drilling/data/tools.toml` and `end_milling/data/tools.toml`, whose comments name the old paths and which spec.md's Edge Cases require to move byte-identical — record that reason in the exclusion list, since it is a deliberate carve-out and not an oversight. Do this **after** T045 and T046, or the widened check fails on them. **Delivered slightly wider than written**: the pattern also gained `mfgparams[./]cli\b`, since T046's finding is the console's old home rather than an `operations/` path and would otherwise have stayed unguarded — this task's own goal names T046 as a class to cover. `\b` keeps it off the current `mfgparams.console.cli`. Verified against the pre-fix blobs: the shipped pattern flags all three original references and none of the corrected ones.
- [X] T048 Confirm CI's `test (3.11)` leg passes on the pull request, per SC-006 (partial). **Done — PR #83's `test (3.11)` check passed**, alongside `test (3.9)`, `test (3.10)` and `test (3.12)`, so SC-006's "the full test suite passes on every supported Python version" is now observed on every interpreter. Why it was open: local `tox` reported `py311: SKIP` throughout this feature — this machine's pyenv exposes no `python3.11` shim and `tox.ini` sets `skip_missing_interpreters = true` — so py39, py310 and py312 were observed green and 3.11 was not, and nothing but CI could close that gap. It was a **post-merge-eligible validation item** per the constitution's Principle XII wording, meaning it could have remained open at merge time provided it was tracked rather than dropped; CI closed it before merge, so that allowance went unused.
