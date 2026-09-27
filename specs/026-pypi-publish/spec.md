# Feature Specification: Automated PyPI Publishing on Merge to Main

**Feature Branch**: `026-pypi-publish`

**Created**: 2026-09-27

**Status**: Draft

**Input**: User description: "Issue #40: Deploy / publish publicly PyPI package (tbc if TestPyPI is recommended). Build a dedicated publish workflow, triggered per the project constitution's existing 'every merge to main MUST publish' requirement, using PyPI Trusted Publishing (OIDC), with a one-time TestPyPI validation before production publishing is enabled."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Version bump on `main` becomes installable automatically (Priority: P1)

As the project maintainer, when I merge a change to `main` that bumps the package's
version, I want the new version to appear on PyPI without me running any manual
build/upload commands, so that `mfgparams` stays continuously installable at its
latest version the same way the project's documentation already stays continuously
published.

**Why this priority**: This is the entire point of the feature (issue #40) and is
already a standing, unmet requirement of the project constitution's Additional
Constraints ("every merge to `main` MUST trigger a workflow that builds and
publishes a new package release to PyPI"). Nothing else in this spec matters if this
does not work.

**Independent Test**: Merge a pull request to `main` that bumps `__version__`, and
confirm the new version becomes installable via `pip install mfgparams==<version>`
without any manual publish action.

**Acceptance Scenarios**:

1. **Given** a pull request that bumps `__version__` and updates the changelog is
   merged to `main`, **When** the resulting CI run on `main` completes successfully,
   **Then** the new version is published to PyPI and installable via
   `pip install mfgparams==<version>` within a short, predictable time window.
2. **Given** a merge to `main` that does not change `__version__` (e.g., a
   docs-only or test-only change), **When** the workflow runs, **Then** no publish
   attempt is made against an already-published version, and the run completes
   without reporting a failure.

---

### User Story 2 - Validate the pipeline safely before it can affect the public listing (Priority: P2)

As the maintainer, I want to prove the publishing pipeline actually works end-to-end
— producing an installable package with correctly rendered metadata — against a
throwaway target before it is trusted to publish to the real, public PyPI listing,
so that a mistake in the pipeline itself cannot corrupt or block the package other
installers depend on.

**Why this priority**: PyPI publishes are effectively permanent (a given version
number can never be reused, even if deleted), so the first real production publish
is a one-way door. This validation happens once, ahead of enabling User Story 1's
automation, not on every future merge.

**Independent Test**: Build and upload the package to TestPyPI, then install it
from TestPyPI into a clean environment and confirm it works, entirely independent
of any change to the production publishing path.

**Acceptance Scenarios**:

1. **Given** the publish pipeline has been built but not yet enabled for the real
   PyPI index, **When** it is run once against TestPyPI, **Then** the resulting
   distribution installs successfully from TestPyPI in a clean environment.
2. **Given** the TestPyPI validation has passed, **When** production publishing is
   subsequently enabled, **Then** no further TestPyPI step is required on routine
   merges (it is a one-time gate, not a recurring dual-publish step).

---

### User Story 3 - No long-lived publish credentials to leak (Priority: P3)

As the maintainer, I want the automated publish step to authenticate to PyPI
without any long-lived secret stored in the repository, so that a leaked CI secret
can never be used by someone else to publish malicious releases under this
package's name.

**Why this priority**: Important defense-in-depth, but the feature still delivers
its core value (Story 1) with a manually-managed API token if this were somehow
unavailable — it is not on the critical path the way Stories 1-2 are.

**Independent Test**: Inspect the repository's configured secrets/environments
after rollout and confirm no PyPI API token is present; the publish step still
succeeds using short-lived, per-run credentials instead.

**Acceptance Scenarios**:

1. **Given** the publish workflow is fully configured, **When** the repository's
   secrets are inspected, **Then** no PyPI API token exists anywhere in the
   repository or its environments.
2. **Given** a publish run executes, **When** it authenticates to PyPI, **Then** it
   does so using a credential that is minted fresh for that run and expires
   immediately after, never a stored long-lived token.

---

### Edge Cases

- What happens when a merge to `main` bumps `__version__` to a value that is not a
  valid, strictly-increasing release version (e.g., malformed, or lower than the
  currently-published version)? The workflow MUST fail visibly rather than attempt
  a publish that PyPI would reject or silently skip.
- What happens when two merges land on `main` in quick succession, both triggering
  the workflow, before the first publish finishes? The second run MUST detect that
  its target version is already published (or in flight) and must not attempt a
  conflicting duplicate publish.
- What happens when PyPI itself is unreachable or rejects the upload for a
  transient reason? The run MUST fail visibly (not swallow the error as a false
  success), and a maintainer MUST be able to retry publishing that already-merged
  commit's version without needing to create a new commit solely to force a retry.
- What happens on a merge to `main` that changes files unrelated to packaging
  (e.g., specs or docs) and does not bump the version? The workflow still runs (per
  the constitutional "every merge" trigger) but MUST complete as a cheap no-op,
  without attempting to re-publish the unchanged, already-published version.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST automatically run the publish workflow on every merge to
  `main`, requiring no manual step to initiate it.
- **FR-002**: System MUST publish a given version to PyPI at most once; a merge
  that does not change the package's version MUST NOT attempt to re-publish or
  produce a duplicate-publish error.
- **FR-003**: Once a version-bump merge lands on `main` and its workflow run
  completes successfully, that version MUST be installable from PyPI
  (`pip install mfgparams==<version>`) without any further manual action.
- **FR-004**: System MUST authenticate to PyPI using short-lived, per-run OIDC
  credentials (Trusted Publishing) and MUST NOT depend on a long-lived API token
  stored as a repository or environment secret.
- **FR-005**: Before production publishing is enabled, the pipeline MUST be
  validated at least once end-to-end against TestPyPI (build, upload, install from
  TestPyPI in a clean environment) as a one-time gate, not a permanent per-merge
  step.
- **FR-006**: System MUST publish the exact package artifact that already passed
  this repository's existing automated test, lint, and build checks for that
  commit, rather than an independently (re)built artifact those checks never
  validated.
- **FR-007**: A run that correctly skips publishing (no version change) MUST be
  distinguishable, from the workflow's reported status, from a run that attempted
  to publish and failed.
- **FR-008**: A maintainer MUST be able to manually re-run the publish step for an
  already-merged commit (e.g., after a transient PyPI outage) without creating a
  new commit solely to force a retry.
- **FR-009**: The rollout of this feature MUST include correcting the project's
  existing PyPI Trusted Publisher registration, which currently references the
  wrong workflow, to reference the workflow this feature adds — documented as a
  manual, one-time setup step, since PyPI's trusted-publisher configuration is not
  something this repository's automation can change on its own.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A version bump merged to `main` becomes installable via
  `pip install mfgparams==<version>` within 10 minutes of the merge, with zero
  manual steps.
- **SC-002**: 100% of merges to `main` that do not change the version complete
  without a duplicate-publish error or a false publish-failure status.
- **SC-003**: Zero long-lived PyPI credentials exist anywhere in the repository's
  configuration at any point after rollout.
- **SC-004**: The publishing pipeline is proven to work, end-to-end, against a
  non-production package index at least once before it is ever allowed to publish
  to the real, public PyPI listing.
- **SC-005**: After a transient publish failure, a maintainer can get the pending
  version published via a single manual retry, with no new commit required.

## Assumptions

- Versioning stays exactly as it is today (Constitution Principle IV): the version
  lives solely in `src/mfgparams/__init__.py`'s `__version__` and is bumped
  manually per release. This feature does not add automatic version-bumping.
- "Publish" means uploading the built source distribution and wheel to the public
  PyPI index (`pypi.org`); TestPyPI is used only for the one-time pre-rollout
  validation in User Story 2, not as an ongoing parallel target.
- The build backend (setuptools) and existing packaging conventions
  (`pyproject.toml`, `src/` layout) are unchanged by this feature; it adds a
  publishing path on top of the already-working build.
- Pre-release identifiers (alpha/beta/rc suffixes) are out of scope; this feature
  covers only stable `MAJOR.MINOR.PATCH` releases reaching `main`.
- The project already has an established changelog and version-bump convention
  (an entry under a dated version heading accompanies each version bump), so this
  feature does not need to define what counts as a "release-worthy" change —
  only how an already-decided version bump reaches PyPI once merged.
