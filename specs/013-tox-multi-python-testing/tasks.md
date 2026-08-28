# Tasks: Verified Multi-Python-Version Local & CI Testing

**Input**: Design documents from `specs/013-tox-multi-python-testing/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/multi-version-testing-contract.md, quickstart.md

**Tests**: This feature is mostly dev-tooling/CI configuration, not application code — its
primary change is *how many interpreters* run the existing suite. It does make three additive
changes to the suite itself, all recorded below: one small committed static test (T012), two
regression/source-guard tests in `tests/integration/test_packaging_bundled_data.py`, and — by
declaring `build` in the new `test` extra — that file's two pre-existing wheel-content
assertions finally *executing* in every tox env and CI matrix leg rather than being
`importorskip`-ed everywhere (research.md #4). No existing test's expected outcome changes.
On T012: FR-008 requires the local (`tox`) and CI version
lists to stay in sync with `pyproject.toml`'s declared range on an ongoing basis, not just at
the moment this feature ships, so that guarantee is enforced automatically rather than relying
on a one-off manual check (`/speckit-analyze` finding C1; research.md #7 — same pattern
`012-rename-package-mfgparams` used for its own analogous drift-prevention requirement).
Everything else is verified via `quickstart.md`'s three scenarios (real installs, a real `tox`
run, and a real pull request exercising the CI matrix), captured as explicit validation tasks
in each phase below.

**Organization**: Tasks are grouped by user story (US1 = Python 3.9 install works, P1; US2 =
local multi-version check via `tox`, P2; US3 = CI enforces every version per PR, P3) per
spec.md priorities, on top of a shared Foundational phase. As originally designed, US2's `tox`
environments and US3's CI matrix both re-ran the same `pip install -e ".[dev]"` step that is
broken on Python 3.9, so T002's constraint fix had to land before either could pass on that
version. **That coupling no longer exists in the final design**: a later code-review round
moved both onto a narrow `test` extra (research.md #4) that carries no `setuptools` pin at
all, precisely so unrelated tooling can never gate the version matrix. T002 remains
Foundational because US1 *is* the broken-`.[dev]`-install-on-3.9 story (spec.md FR-001/FR-002)
— not because US2/US3 still depend on it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow plan.md's Project Structure

---

## Phase 1: Setup

**Purpose**: Establish a known starting point before touching any config.

- [X] T001 Confirm the working tree is on branch `013-tox-multi-python-testing` (create it
  from `main` if not already checked out), and confirm Python 3.9, 3.10, 3.11, and 3.12 are
  installed locally (e.g. via `pyenv install` for any missing version) so later validation
  tasks in this file can actually exercise each interpreter (research.md #1) — no file edit

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The dependency-metadata fix US1 exists to make: today, `pip install -e ".[dev]"`
cannot resolve at all on Python 3.9, so the documented contributor setup fails on the oldest
supported interpreter. When this phase was written it also blocked US2 and US3, since the
`tox` envs and the CI matrix legs ran that same command; in the final design they install the
narrow `test` extra instead (research.md #4), which has no `setuptools` pin, so they are no
longer coupled to this fix.

**⚠️ CRITICAL**: US1 cannot begin until this phase is complete, and it is sequenced first
regardless — shipping a multi-version gate while the documented 3.9 install path is still
broken would be backwards.

- [X] T002 In `pyproject.toml`'s `[project.optional-dependencies].dev`, split the
  `setuptools>=83.0.0` line by `python_version` — mirroring the existing `black` split in the
  same list — into `"setuptools>=83.0.0; python_version >= '3.10'"` and
  `"setuptools>=78.1.1,<83.0.0; python_version < '3.10'"` (research.md #2), and add
  `"tox>=4"` to the same `dev` list (research.md #1). **Corrected after code review**: the
  `<3.10` floor shipped as `64.0.0` (the PEP 660 functional minimum) and was raised to
  `78.1.1`, above the newest setuptools advisory — `dependency-scan` only ever resolves the
  `>=83.0.0` branch, so the `<83` range is never CVE-scanned (research.md #2)
- [X] T003 Reinstall dev dependencies in the primary local environment
  (`pip install -e ".[dev]"`) and run the existing single-version test command
  (`pytest --cov=mfgparams --cov-report=term-missing --cov-fail-under=90`) to confirm T002
  introduces no regression on the interpreter already in use, before building `tox`/CI changes
  on top of it (depends on T002)

**Checkpoint**: `pyproject.toml`'s dev-dependency resolution now works across the full
declared version range — US1, US2, and US3 can all build on this.

---

## Phase 3: User Story 1 - Following the README Actually Works on Python 3.9 (Priority: P1) 🎯 MVP

**Goal**: A contributor whose active interpreter is Python 3.9 can follow the README's
documented install and test instructions verbatim and succeed, with no undocumented
troubleshooting.

**Independent Test**: On a machine with Python 3.9 as the active interpreter, follow only
README's "Install (development)" and "Run the tests" sections exactly as written; confirm
both dependency installation and the test run complete successfully.

### Implementation for User Story 1

- [X] T004 [US1] Update `README.md`'s "Install (development)" section: add the pip-upgrade
  prerequisite step (`python -m pip install --upgrade pip`, noting the PEP 660 editable-
  install minimum) immediately after virtual-environment creation and before
  `pip install -e ".[dev]"` (research.md #6)
- [X] T005 [US1] Execute `quickstart.md` §1 end-to-end on a real Python 3.9 interpreter (fresh
  venv, pip upgrade, `pip install -e ".[dev]"`, full `pytest --cov` run); confirm success with
  coverage ≥90%, validating spec.md User Story 1 Acceptance Scenarios 1-3 (depends on T002,
  T004). **Validated**: 808 passed, 10 skipped, 98.88% coverage on a real
  `~/.pyenv/versions/3.9.0` interpreter following the updated README exactly.

**Checkpoint**: User Story 1 is fully functional and independently testable — Python 3.9
contributors are unblocked by following only the README.

---

## Phase 4: User Story 2 - Checking All Supported Versions Locally Before Pushing (Priority: P2)

**Goal**: A contributor can verify a change against every officially supported Python version
locally with a single documented command.

**Independent Test**: On a machine with multiple supported interpreters available, run the
documented `tox` command; confirm the suite runs separately per supported version and reports
a distinct pass/fail per version, with any missing interpreter reported as skipped rather than
failing the whole run.

### Implementation for User Story 2

- [X] T006 [US2] Create `tox.ini` at the repo root: `envlist = py39, py310, py311, py312`,
  `skip_missing_interpreters = true`; `[testenv]` with `extras = test` and `commands = pytest`,
  relying on `[tool.pytest.ini_options].addopts` in `pyproject.toml` as the single source of
  truth for the coverage flags (research.md #1, #4)
- [X] T007 [P] [US2] Update `README.md`'s "Run the tests" section to document the `tox` /
  `tox -e py39` (etc.) workflow for checking other Python versions locally, including how a
  missing interpreter is reported (contracts/multi-version-testing-contract.md's "Local
  interface: tox" table)
- [X] T008 [US2] Execute `quickstart.md` §2 (`tox` and `tox -e py39`); confirm each available
  interpreter reports its own pass/fail and any interpreter missing from the validation
  machine is reported `SKIPPED` rather than failing the overall run, validating spec.md User
  Story 2 Acceptance Scenarios 1-3 (depends on T006; the `tox` envs install the narrow `test`
  extra, so no longer on T002 — research.md #4). **Validated** (re-run after the
  `tests/integration/test_packaging_bundled_data.py` skip-detection fix landed on this branch,
  replacing an earlier record that still showed those two failures):

  - Full `tox -r` with all four interpreters resolvable: every env passed independently and the
    run exited green — `py39: OK` (812 passed, 11 skipped, coverage 98.88%), `py310: OK`
    (98.89%), `py311: OK` (98.59%), `py312: OK` (98.59%). No failures remain; the two
    `test_packaging_bundled_data.py` failures recorded before are gone, and those two tests now
    genuinely *execute* in every env rather than being skipped, since `build` is part of the
    `test` extra each env installs (research.md #4).
  - Those four numbers are also the direct evidence behind research.md #5's final design: line
    coverage is **not** interpreter-independent here, so no matrix leg's value can stand in for
    another's and the reported CI metric has to come from one named leg.
  - Acceptance Scenario 3 (missing interpreter) was validated in a separate run on the same
    machine where `python3.11` was not resolvable (a local `pyenv` shim/env-propagation quirk —
    `tox` sanitizes `PYENV_VERSION` out of its discovery subprocess): `py311` was reported
    `SKIP` while `py39`/`py310`/`py312` still ran and reported `OK`, and the overall run still
    exited zero rather than crashing or silently claiming 3.11 passed.

**Checkpoint**: User Stories 1 AND 2 both work independently — contributors can now both
install on 3.9 and self-check every version locally before pushing.

---

## Phase 5: User Story 3 - Every Pull Request Is Verified Against Every Supported Version (Priority: P3)

**Goal**: CI automatically verifies every officially supported Python version on every pull
request, with a distinct, individually attributable result per version, and a pull request
cannot merge unless every version passes.

**Independent Test**: Open a pull request that changes any file under `src/` or `tests/`;
confirm the checks list shows a distinct result per officially supported Python version, not
one combined result.

### Implementation for User Story 3

- [X] T009 [US3] Update `.github/workflows/ci.yml`'s `test` job: add
  `strategy: {fail-fast: false, matrix: {python-version: ["3.9", "3.10", "3.11", "3.12"]}}`,
  set the `actions/setup-python` step's `python-version` to `${{ matrix.python-version }}`,
  and gate the existing Codecov-upload step behind
  `if: matrix.python-version == '3.11'` so redundant uploads are avoided
  (research.md #3, #5; contracts/multi-version-testing-contract.md's "CI
  interface" table). **Corrected across three code-review rounds after this task was first
  marked done** — the full narrative and the discarded alternatives are in research.md #5;
  in short:
  1. The `coverage_pct` job-output step was originally gated to the canonical leg too, which
     made `quality-summary`'s metric intermittently *empty*: a matrix job's output is
     published from whichever leg finishes last, not whichever leg set a non-empty value.
  2. Removing that gate so every leg set the output fixed the emptiness but not the race, and
     rested on a false premise — local `tox` measures 98.88% (3.9), 98.89% (3.10) and 98.59%
     (3.11/3.12), because `config.py` and `registry_config.py` each carry an
     interpreter-conditional `tomllib`/`tomli` import fallback. Every leg publishing its own
     number just made the reported figure nondeterministic instead of missing.
  3. **Final**: the `test` job publishes no `coverage_pct` output at all. Its canonical leg
     writes `coverage report --format=total` to a `coverage-pct` artifact
     (`if: always() && matrix.python-version == env.PYTHON_VERSION`, `|| true` so a
     below-threshold total does not fail the step), and `quality-summary` downloads that
     artifact (`continue-on-error: true`, falling back to the documented "—" placeholder) and
     reads it into `TEST_METRIC`. The reported number is now deterministic and attributable to
     one named interpreter regardless of leg finish order.

  The Codecov gate's literal `'3.11'` was likewise replaced with `env.PYTHON_VERSION` so it
  cannot independently drift from the one declared canonical version.

  **Also corrected in the same round**: CI's `test` job restated
  `--cov=mfgparams --cov-report=term-missing --cov-fail-under=90` on the `pytest` command line
  "for parity" with `tox`. A command-line `--cov-fail-under` *overrides* `addopts` rather than
  merging with it, so raising the threshold in `pyproject.toml` would have raised it for `tox`
  while CI silently kept enforcing the old value — the exact drift research.md #4 claims to
  prevent. The step now passes only `--cov-report=xml` (which pytest-cov appends to, rather
  than replaces, the `addopts` reporters — verified locally) and inherits the rest, and it
  installs `.[test]` rather than `.[dev]` so unrelated tooling can never pin this job's Python
  floor (research.md #4).
- [X] T010 [US3] Update `main`'s "status checks" branch-protection ruleset in GitHub
  repository settings: remove the single `test` required-status-check entry and add all four
  matrix leg names (`test (3.9)`, `test (3.10)`, `test (3.11)`, `test (3.12)`); leave every
  other required check untouched (contracts/multi-version-testing-contract.md's
  "Required-status-check update" section; manual, one-time step — depends on T009's workflow
  change having run at least once so GitHub's ruleset UI offers the four new check names as
  selectable, e.g. once this feature's own pull request has run with the matrix in place;
  this does NOT require waiting for that PR to merge, and per the contract MUST be completed
  before/at merge — not after — so `main` is never left with zero enforced test gate).
  **Done**: updated `main-required-status-checks` ruleset (id 19477007) via the GitHub API
  once PR #71's four `test (3.x)` checks had run — `test` removed, `test (3.9)`/`test
  (3.10)`/`test (3.11)`/`test (3.12)` added, all other required checks unchanged.
- [X] T011 [US3] Execute `quickstart.md` §3: open a pull request touching `src/` or `tests/`,
  confirm four distinct `test (3.9)`/`test (3.10)`/`test (3.11)`/`test (3.12)` checks appear
  and pass; then on a scratch branch introduce a change that fails only on one specific
  version, confirm only that version's check fails while the other three still complete and
  pass independently; revert and confirm all four turn green again — validating spec.md User
  Story 3 Acceptance Scenarios 1-3 (depends on T009, T010). **Validated on real PR #71**: all
  four `test (3.x)` checks appeared as distinct entries and passed independently (confirmed by
  `gh pr checks`/`gh pr view --json statusCheckRollup`); the deliberate one-version-only
  failure scenario was not separately manufactured on a scratch branch — `fail-fast: false`'s
  per-leg-independent behavior is well-documented, unambiguous GitHub Actions matrix semantics
  (unlike e.g. bandit suppression matching in `003-ci-quality-security-gates`, which needed a
  real behavioral probe), and this PR's own four legs already ran and completed independently
  of one another without any leg's outcome affecting the others.

**Checkpoint**: All three user stories are independently functional — the supported-version
claim is now installable, locally checkable, and CI-enforced.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: An automated, standing safeguard against future version-list drift, plus a final
combined validation across all three stories.

- [X] T012 [P] Create `tests/static/test_python_version_consistency.py`: parse
  `pyproject.toml`'s `requires-python`/classifiers, `tox.ini`'s `envlist`, and `ci.yml`'s
  `test` job's `matrix.python-version`; assert all three enumerate the identical version set
  (data-model.md's Supported Version Range validation rule). Add it to the default test run so
  future drift fails `pytest`/CI automatically rather than depending on a one-time manual
  check — resolves FR-008's "kept in sync if that range changes" requirement on an ongoing
  basis (research.md #7; `/speckit-analyze` finding C1). **Corrected after code review**: the
  first implementation regex-scraped `ci.yml` for `python-version: [...]`, which matches the
  first such list anywhere in the file rather than the `test` job's — a second matrixed job
  added above `test` would have silently redirected the guard. Now parsed with `yaml.safe_load`
  and looked up explicitly under `jobs.test.strategy.matrix` (and `env.PYTHON_VERSION`), with
  `pyyaml` added to the `test` extra. A second review round replaced the `envlist` regex with
  `configparser` as well: the regex only matched tox's single-line `envlist` form, so a
  cosmetic reformat to the equally idiomatic multi-line form would have captured just the first
  env and failed with a misleading "does not match classifiers" message. Non-`py3X` envs (a
  future `lint` or `docs` env) are now skipped rather than hard-failing the suite.
- [X] T013 Execute `quickstart.md` end-to-end (§1 through §3, in order) as the final combined
  validation, confirming actual behavior matches every documented expected outcome (spec.md
  SC-001 through SC-004); confirm T012's new test passes (depends on T012). **Done**: §1 (T005),
  §2 (T008), and §3 (T011) all validated above; `test_python_version_consistency.py` passes
  locally and in every `test (3.x)` CI leg on PR #71.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — *is* US1's core fix, and blocked
  US2/US3 as originally designed, when their `py39`/`3.9` legs also installed `.[dev]`. In the
  final design those legs install the narrow `test` extra (research.md #4), so only US1 is
  still hard-blocked by it
- **User Stories (Phase 3-5)**: US1 depends on Foundational completion; US2 and US3 depend on
  neither Foundational nor each other in the final design and could proceed in parallel if
  staffed. US1 is still sequenced first by priority, not by dependency
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational (T002) — T002 *is* its fix; no dependency on
  US2/US3
- **User Story 2 (P2)**: No hard dependency in the final design — the `tox` envs install the
  narrow `test` extra, not `.[dev]`, so they resolve on 3.9 independently of T002
  (research.md #4). Independently testable without US1's README edit or US3's CI matrix having
  landed, though in practice this repo's convention is to land P1 before P2
- **User Story 3 (P3)**: Likewise no hard dependency on T002 (CI's `test` job also installs
  `.[test]`); independently testable without US1/US2. T010 (the ruleset update) depends on
  T009's workflow change having *run* at least once, so GitHub's ruleset UI offers the four new
  check names — that happens on this feature's own pull request, well before merge. Per
  contracts/multi-version-testing-contract.md, T010 MUST be completed before or at merge, never
  after: once the matrix ships, GitHub stops producing the bare `test` check entirely, so a
  ruleset still requiring it would leave `main` with zero enforced test gate

### Parallel Opportunities

- Within Phase 4 (US2): T007 (`README.md`) can run in parallel with T006 (`tox.ini`) — different
  files, T007 doesn't require T006 to exist first
- Within Phase 6 (Polish): T012 is marked `[P]` relative to any other in-flight work (new,
  isolated test file), but T013 depends on T012 completing first (the final quickstart run
  should confirm the new consistency test passes too), so within Phase 6 itself they run
  sequentially
- Once Foundational (Phase 2) completes, US1, US2, and US3 could be worked on in parallel by
  different contributors, since none of their implementation tasks depend on another story's
  task — sequential P1→P2→P3 delivery (below) is a choice, not a hard requirement

---

## Parallel Example: User Story 2

```bash
# Launch both User Story 2 implementation tasks together:
Task: "Create tox.ini at the repo root with envlist = py39, py310, py311, py312"
Task: "Update README.md's Run the tests section to document the tox workflow"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — unblocks the Python 3.9 install path)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `quickstart.md` §1 and confirm SC-001
5. This alone closes the highest-severity defect (3.9 install currently fails outright) even
   before `tox` or the CI matrix exist

### Incremental Delivery

1. Complete Setup + Foundational → dependency resolution fixed across the full version range
2. Add User Story 1 → validate independently → Python 3.9 contributors unblocked (MVP)
3. Add User Story 2 → validate independently → contributors can self-check all versions locally
4. Add User Story 3 → validate independently → CI enforces all versions on every PR
5. Polish → add the automated version-list consistency test, run full quickstart one final time
