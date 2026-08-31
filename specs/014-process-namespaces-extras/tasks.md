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
- [X] T014 [US1] Update the four `operations/**/data/*.toml` globs in `[tool.setuptools.package-data]` in `pyproject.toml` to their `processes/machining/**` paths

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
- [X] T022 [US2] Create `src/mfgparams/console/__main__.py` delegating to `mfgparams.console.cli.main`
- [X] T023 [US2] Rewrite `src/mfgparams/__main__.py` to define its own `main()` that imports the console **inside the function body**, wrapped in the FR-011 guard exactly as specified in contracts/console-entry-contract.md § *What the guard actually wraps* — the `try` encloses the lazy console import, and any `ModuleNotFoundError` whose `exc.name` roots at `mfgparams` is re-raised rather than reported as a missing extra
- [X] T024 [US2] Confirm `[project.scripts] mfgparams = "mfgparams.__main__:main"` still resolves after T023, since `__main__.py` now defines `main` rather than re-exporting it

### Packaging and messages

- [X] T025 [P] [US2] Add `console = []` and `all = ["mfgparams[console]"]` to `[project.optional-dependencies]` in `pyproject.toml`, with a comment recording why the extra is declared while empty (contracts/installation-extras-contract.md). `all` is a **self-referential extra**, which pip only resolves from 21.2 onward; that is now a load-bearing floor rather than an incidental one, so keep the README's existing `python -m pip install --upgrade pip` step (README line 37, currently justified by PEP 660) and record the second reason beside it.
- [X] T026 [P] [US2] Add the missing-console message to `src/mfgparams/locales/en.py` under a stable ID, with a comment stating it MUST stay in the core catalogue when slice 015 relocates the others (research.md #4)
- [X] T027 [P] [US2] Rewrite `mfgparams.cli` imports across `tests/` to `mfgparams.console.cli`

### Tests for User Story 2

- [X] T028 [P] [US2] Add `tests/static/test_core_does_not_import_console.py`: parse every module under `src/mfgparams/` except `__main__.py` with `ast` and fail on any import naming `mfgparams.console` (FR-008)
- [X] T029 [P] [US2] Add a runtime assertion to the same file that importing `mfgparams` and each `processes.machining.*` module leaves `mfgparams.console` absent from `sys.modules` — this is what keeps `__main__.py`'s exemption honest (FR-008)
- [X] T030 [P] [US2] Add a test named `test_console_missing_dependency_*` asserting the guard emits one actionable message naming `pip install mfgparams[console]` on stderr, exits non-zero, and raises no traceback. Simulate the failure by making a non-`mfgparams` module the console imports unresolvable (e.g. `monkeypatch.setitem(sys.modules, "<dep>", None)`), never by patching the guard itself. Add the companion case too: a `ModuleNotFoundError` naming an `mfgparams.*` module must propagate, not be swallowed (FR-011)
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
- [X] T038 [P] [US3] Update the README's structure and installation sections to show the process-qualified paths and the three install commands (FR-016)

**Checkpoint**: All three stories complete; nothing points at the old layout.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T039 Add the `## [Unreleased]` CHANGELOG entry describing the restructure as breaking, explicitly noting no version bump is cut by this feature (FR-018)
- [ ] T040 Run every section of [quickstart.md](./quickstart.md) end to end and fix any drift between it and the delivered code
- [ ] T041 Run the full gate set: `tox` (py39–py312), `tox -e packaging`, `ruff check .`, `black --check .`, `mypy`, `python scripts/check_maintainability.py src/ scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py`, `bandit -r src scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py -ll` (invocations copied from `.github/workflows/ci.yml`, so local runs match CI)
- [ ] T042 Confirm coverage is at or above 90% and update the README coverage badge/number if it moved (Principle VII, SC-006)
- [ ] T043 Self-review the diff against the Development Workflow checklist in `.specify/memory/constitution.md` — in particular that the move commits contain no content edits beyond import lines
- [ ] T044 Run `/speckit-analyze` to cross-check spec, plan and tasks before opening the pull request

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
