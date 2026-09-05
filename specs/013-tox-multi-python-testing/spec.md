# Feature Specification: Verified Multi-Python-Version Local & CI Testing

**Feature Branch**: `013-tox-multi-python-testing`

**Created**: 2026-08-26

**Status**: Draft

**Input**: User description: "Fix local test-running experience and Python version support
verification: (1) pyproject.toml's dev extra unconditionally pins setuptools>=83.0.0, which
requires Python>=3.10, contradicting the project's requires-python>=3.9 and README's "targets
Python 3.9+" claim — `pip install -e ".[dev]"` currently fails to resolve on a real Python 3.9
interpreter; (2) CI (.github/workflows/ci.yml) only runs the test job on a single pinned Python
3.11, so the 3.9-3.12 support claimed in pyproject.toml's classifiers is never actually
verified anywhere; (3) there is no tox (or equivalent) configuration, so contributors have no
easy way to run the test suite locally against each supported Python version. Add a tox.ini
covering py39-py312 that runs the same pytest command CI uses (with coverage gate), fix the
setuptools version constraint in pyproject.toml's dev extra so `pip install -e ".[dev]"`
resolves correctly on Python 3.9 (following the existing python_version-conditioned pattern
already used for the black dependency in the same extra), expand the CI test job to a full
3.9/3.10/3.11/3.12 matrix so the supported-version claim is actually enforced on every PR, and
update README.md's "Run the tests" section to document both the plain `pytest` workflow and how
to use tox to check other Python versions locally, including the pip-upgrade caveat that's
required for editable installs to work on older bundled pip versions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Following the README Actually Works on Python 3.9 (Priority: P1)

A new contributor clones the project on a machine whose default (or only) Python interpreter
is 3.9 — the oldest version the project claims to support — and follows the README's
documented install and test instructions exactly as written. The install and test run both
succeed, with no undocumented troubleshooting required.

**Why this priority**: This is the core defect being fixed. The project currently advertises
"Python 3.9+" in its README and packaging metadata, but the documented install command cannot
resolve its own dev dependencies on Python 3.9. Anyone on the oldest supported version who
trusts the documentation is currently blocked before they can run a single test — that's the
highest-value, most user-visible problem to close first.

**Independent Test**: On a machine with Python 3.9 as the active interpreter, follow only the
README's "Install (development)" and "Run the tests" sections verbatim; confirm dependency
installation and the test run both complete successfully.

**Acceptance Scenarios**:

1. **Given** a Python 3.9 interpreter and a clean virtual environment, **When** a contributor
   runs the documented dev-dependency install command, **Then** it completes successfully with
   no dependency-resolution error.
2. **Given** dev dependencies installed under Python 3.9, **When** a contributor runs the
   documented test command, **Then** the full test suite runs and the coverage gate is
   evaluated, exactly as it would on any other supported version.
3. **Given** a contributor whose default system `pip` predates support for modern editable
   installs, **When** they follow the README's install instructions, **Then** the
   instructions themselves lead to a successful install (e.g., by calling out any needed
   prerequisite step) rather than failing with an unexplained error.

---

### User Story 2 - Checking All Supported Versions Locally Before Pushing (Priority: P2)

A contributor has made a change and wants to confirm it behaves correctly on every Python
version the project claims to support — not just whichever version happens to be active in
their shell — before opening a pull request. They run a single, documented local command and
get a clear pass/fail result per version.

**Why this priority**: This directly prevents the class of bug this feature exists to catch:
changes that pass on one interpreter but silently break on another supported one. It's ranked
below Story 1 because a contributor who can't even install dev dependencies (Story 1) can't
reach this workflow at all, but it's still core to the feature's purpose, distinct from the
CI-side guarantee in Story 3.

**Independent Test**: On a machine with multiple supported Python interpreters available, run
the documented single local command; confirm the test suite (including the coverage gate) runs
separately against each supported version and reports a distinct result per version.

**Acceptance Scenarios**:

1. **Given** all officially supported Python interpreters are available locally, **When** a
   contributor runs the documented local multi-version test command, **Then** the test suite
   runs once per supported version and a clear pass/fail result is reported for each.
2. **Given** a change that fails only under one specific supported Python version, **When** the
   contributor runs the documented local multi-version test command, **Then** the failure is
   attributed to that specific version and the other versions still report their own results.
3. **Given** a contributor's machine is missing one or more of the supported interpreters,
   **When** they run the documented local multi-version test command, **Then** the missing
   versions are clearly reported as skipped/unavailable rather than causing the entire run to
   fail or silently passing as if verified.

---

### User Story 3 - Every Pull Request Is Verified Against Every Supported Version (Priority: P3)

A maintainer reviewing a pull request wants confidence that the change has actually been
tested against every Python version the project claims to support, without relying on each
contributor to remember to check locally.

**Why this priority**: This closes the loop so the guarantee doesn't depend on individual
contributor diligence — it's the automated backstop for Stories 1 and 2. It's ranked last by
value, not by dependency: as originally designed it would have needed Story 1's dependency fix
first (CI's matrix legs ran the same `pip install -e ".[dev]"` that fails on 3.9), but the
implemented design installs a narrow `test` extra in CI instead, which carries no `setuptools`
pin — so this story is independently implementable (plan.md research.md #4; tasks.md's User
Story Dependencies).

**Independent Test**: Open a pull request that changes any file under `src/` or `tests/`;
confirm the CI checks section shows a distinct, individually reportable test result for each
officially supported Python version, not one combined or single-version result.

**Acceptance Scenarios**:

1. **Given** a pull request with no version-specific defect, **When** CI runs, **Then** a
   distinct test result (including the coverage gate) is shown for each officially supported
   Python version, and all pass.
2. **Given** a pull request that introduces a change which only fails under one specific
   supported Python version, **When** CI runs, **Then** only that version's check fails and
   clearly identifies which version failed, while the others pass independently.
3. **Given** a pull request that passes on the previously-sole-tested version, **When** CI runs
   the full version set, **Then** the pull request cannot merge until every supported version's
   check passes (subject to the project's existing required-status-check policy).

---

### Edge Cases

- What happens when a contributor runs the plain, single-version test command (not the
  multi-version workflow) — it MUST continue to work exactly as before, unaffected by this
  feature, so existing muscle memory and any other documentation referencing it stays valid.
- How does the local multi-version workflow behave when none of the supported interpreters
  besides the contributor's default are installed at all — it must report that clearly rather
  than appearing to hang or fail opaquely.
- What happens when the project's officially supported version range changes in the future
  (a version is added or dropped) — the local multi-version workflow and the CI version matrix
  must be updated together, since a mismatch between them would silently reintroduce the same
  kind of unverified-claim gap this feature closes.
- What happens when a dev-only tool needed for testing/tooling itself only supports a subset of
  the officially supported Python range — the install process must resolve correctly on every
  officially supported version regardless, even if that means using different tool versions per
  Python version.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Installing the project's development dependencies MUST succeed, without manual
  workarounds, on every Python version within the project's officially declared supported range
  (currently 3.9 through 3.12).
- **FR-002**: The documented steps for installing development dependencies and running the test
  suite MUST result in a successful test run when followed exactly as written, on any
  officially supported Python version — including any prerequisite step (such as ensuring the
  installer tool itself is new enough) needed for that success.
- **FR-003**: Contributors MUST be able to run the identical test suite and coverage
  requirement locally against each individually supported Python version via a single
  documented command, without hand-building a separate environment per version themselves.
- **FR-004**: When a contributor's machine lacks one or more officially supported Python
  interpreters, the local multi-version test workflow MUST clearly report which versions were
  unavailable/skipped, rather than silently treating them as passed or failing the entire run
  because of the absence alone.
- **FR-005**: The automated pull-request pipeline MUST execute the test suite, including the
  existing coverage requirement, separately against every officially supported Python version
  on every pull request. **Qualified by `specs/016-ci-path-based-selection`**: "every pull
  request" now means every pull request touching a path that feature's `test` category
  actually depends on — a pull request touching only `specs/**` or a non-packaging root `*.md`
  file skips `test` entirely (intentionally; see that spec's contracts/path-selection-contract.md),
  the same way `lint`/`complexity`/`typecheck`/`security`/`build`/`docs` do.
- **FR-006**: The automated pull-request pipeline MUST report a distinct, individually
  attributable result per Python version, so a failure specific to one version is identifiable
  without needing to inspect combined logs.
- **FR-007**: A pull request MUST NOT be mergeable unless the test suite (with its coverage
  requirement) passes for every officially supported Python version, consistent with the
  project's existing required-status-check policy. **Qualified by
  `specs/016-ci-path-based-selection`**: this applies when `test` actually runs (see FR-005's
  qualification) — `ci-ok`'s aggregate predicate treats an intentional path-based skip of
  `test` as non-blocking, not as a bypass of this requirement.
- **FR-008**: The set of Python versions exercised by the local multi-version workflow and the
  set exercised by the automated pull-request pipeline MUST match the officially supported
  version range declared in the project's packaging metadata, and MUST be kept in sync if that
  range changes.
- **FR-009**: The project's documentation MUST describe both the plain single-version test
  command and the local multi-version workflow, including any prerequisite step needed for the
  single-version install/test flow to succeed on the oldest supported version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A contributor whose active Python interpreter is the oldest officially supported
  version can complete dependency installation and a full test run by following only the
  documented instructions, on the first attempt, with zero undocumented troubleshooting steps.
- **SC-002**: A contributor can verify a change against every officially supported Python
  version locally by running one documented command, with no manual per-version environment
  setup.
- **SC-003**: 100% of pull requests merged after this feature ships have a recorded,
  individually visible pass result for every officially supported Python version. **Qualified
  by `specs/016-ci-path-based-selection`**: for pull requests where `test` runs at all (see
  FR-005's qualification) — a specs-only or non-packaging-`*.md`-only pull request has no
  per-version result to show, by design, and is not a counterexample to this criterion.
- **SC-004**: Zero pull requests are merged where the change was only ever verified against a
  single Python version, measured by whether the required per-version checks appear and pass on
  every pull request going forward that touches a path `test` depends on (see FR-005's
  `specs/016-ci-path-based-selection` qualification).

## Assumptions

- The officially supported Python version range remains 3.9 through 3.12, as currently declared
  in the project's packaging metadata (`requires-python` and classifiers); this feature verifies
  and enforces that existing claim rather than changing which versions are supported.
- Contributors running the local multi-version workflow will not necessarily have every
  supported interpreter installed on their machine; gracefully reporting missing versions as
  skipped, rather than requiring all of them to be present, is acceptable.
- The ≥90% coverage threshold and which suites remain opt-in (e.g., the performance suite) are
  unchanged by this feature; the primary change is the set of Python versions the suite is
  verified against and the ease of doing so locally. **Two deliberate exceptions**, both
  additive and both discovered while implementing this feature: declaring `build` as a test
  dependency makes `tests/integration/test_packaging_bundled_data.py`'s wheel-content
  assertions *execute* in automation instead of being `importorskip`-ed everywhere (they
  asserted nothing before — research.md #4). They ran in every tox env and CI matrix leg
  until issue #75 P1.3 moved them to CI's `build` job and `tox -e packaging`, where they
  run once; both remain merge-blocking. And two small
  regression/source-guard tests were added to that same file to protect the skip guard itself.
  No existing test changes its expected outcome, and no opt-in suite becomes default.
- The increase in automated pipeline time/cost from testing against multiple Python versions
  per pull request, instead of one, is an accepted tradeoff in exchange for the supported-version
  claim actually being enforced.
