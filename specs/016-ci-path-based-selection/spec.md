# Feature Specification: CI Path-Based Job Selection

**Feature Branch**: `016-ci-path-based-selection`

**Created**: 2026-09-05

**Status**: Draft

**Input**: User description: "016-ci-path-based-selection: Restructure CI workflows so jobs run only for the paths they actually cover (part of issue #63 restructure, slice 3 of 4 — see specs/014-process-namespaces-extras and specs/015-console-i18n-relocation for prior slices and conventions). Branch from main."

## Context

This feature is **slice 3 of 4** of [issue #63](https://github.com/kniklas/mfgparams/issues/63)
("change repository and package structure"), per the agreed decomposition in
[the plan comment on #63](https://github.com/kniklas/mfgparams/issues/63#issuecomment-5470725460).
Slice 1 ([014](../014-process-namespaces-extras/spec.md)) grouped calculations process-first and
split the console behind an installation extra; slice 2 ([015](../015-console-i18n-relocation/spec.md))
relocated console message catalogues. Both are merged to `main`. This slice could not be designed
before 014 landed, because it depends on 014's directory layout (`src/mfgparams/processes/**`,
`src/mfgparams/console/**`) existing to have a real path structure to select on.

Deliberately **not** in this slice:

| Slice | Scope | Why separate |
|---|---|---|
| 017 | Placeholder namespaces for not-yet-implemented processes (turning, welding, joining, forming) | Trivial and independent; no CI dependency |

This is the last *infrastructure* slice; 017 is the last *code* slice. Changes accumulate under
`## [Unreleased]` for the single `2.0.0` issue #63 will cut once slice 017 lands — no release is
cut in this slice.

### Current state

`.github/workflows/ci.yml` runs every quality-check job (`lint`, `complexity`, `typecheck`,
`security`, `dependency-scan`, `test`, `build`, `docs`) on every `push`/`pull_request`, regardless
of which files changed. A documentation-only change to `docs/source/*.rst`, a spec-only change
under `specs/**`, or a skill-only change under `.github/skills/**` currently pays for the full
Python toolchain: four `test` matrix legs, `build`'s wheel assertions, `mypy`, `bandit`, `pip-audit`,
and a Sphinx build — none of which that change could plausibly have broken.

A single aggregate required check, `ci-ok` (issue #75 P2.4), already asserts that every job it
lists in `needs:` reported `success`. That job's own comment explicitly warns that adding a job to
its `needs:` list silently promotes it to a merge blocker; the same care applies in reverse here —
if a job starts being conditionally skipped, `ci-ok` must keep treating an *intentional* skip as
non-blocking while still catching a *real* failure. Getting this wrong reintroduces exactly the
decorative-guard failure mode `code-review/SKILL.md` §7a already flags as CRITICAL.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Docs-only and spec-only changes skip the Python toolchain (Priority: P1)

As a contributor opening a pull request that only touches `docs/source/**`, `specs/**`, or other
non-code paths, I want CI to skip jobs that only validate Python source (`lint`, `complexity`,
`typecheck`, `security`, `test`, `build`) so that my PR gets a signal back in roughly the time one
relevant job takes, not eight. **`.github/skills/**`/`.claude/**` are a deliberate partial
exception**: a skill-only change still runs `lint` (it verifies skill symlinks — see
data-model.md's Path Category Corrections note #4), skipping only the other five Python-toolchain
jobs, which have nothing to check for that path.

**Why this priority**: This is the concrete, everyday cost the feature exists to remove — every
prior restructure slice (014, 015) itself produced spec-only commits mid-flight (`/speckit-clarify`,
`/speckit-plan` artifact updates) that paid the full CI bill for zero code risk.

**Independent Test**: Open a pull request that changes only a file under `specs/**`; confirm the
Python-toolchain jobs report as skipped (not run), the change still merges once the jobs that do
apply (if any) pass, and `ci-ok` reports success rather than being blocked by the skips.

**Acceptance Scenarios**:

1. **Given** a pull request that changes only files under `specs/**`, **When** CI runs, **Then**
   `lint`, `complexity`, `typecheck`, `security`, `test`, and `build` are skipped, and `ci-ok`
   still reports success.
2. **Given** a pull request that changes only files under `docs/source/**`, **When** CI runs,
   **Then** the `docs` job runs and the Python-toolchain jobs above are skipped.
3. **Given** a pull request that changes both a file under `specs/**` and a file under `src/**`,
   **When** CI runs, **Then** every job whose paths matched runs normally — mixed changes never
   silently drop coverage for the code half.

---

### User Story 2 - A real failure still blocks the merge (Priority: P1)

As a maintainer relying on `ci-ok` as the single required status check, I want a job that *should*
have run and genuinely failed to still block the merge, indistinguishable in outcome from today,
so that path-based selection never becomes a way to accidentally merge broken code.

**Why this priority**: Equal priority to User Story 1 — a selection mechanism that saves CI time by
also hiding real failures is worse than the problem it solves, and is the specific risk the
`ci-ok` job's own comments already warn about for a different reason (job renames).

**Independent Test**: Open a pull request that changes a file under `src/**` and introduces a lint
violation; confirm `lint` runs, fails, and `ci-ok` reports failure exactly as it does today.

**Acceptance Scenarios**:

1. **Given** a pull request that changes `src/mfgparams/**` and fails `mypy`, **When** CI runs,
   **Then** `typecheck` reports failure and `ci-ok` reports failure.
2. **Given** a pull request that changes only `specs/**` (so `typecheck` is skipped), **When**
   `ci-ok` evaluates its dependencies, **Then** it treats that skip as non-blocking rather than
   reporting failure or leaving the PR without a resolved status.

---

### User Story 3 - Changes to CI configuration itself are always fully validated (Priority: P2)

As a maintainer reviewing a change to `.github/workflows/ci.yml` or the path-selection rules
themselves, I want every job to run regardless of path filtering so that a change to the filtering
logic is validated by the full suite it controls, not exempted by its own new rules.

**Why this priority**: A narrower, safety-net case of User Story 2 — the one path where a bug in
this feature's own logic could be invisible precisely because that logic decides what runs.

**Independent Test**: Open a pull request that changes only `.github/workflows/ci.yml`; confirm
every job that runs today still runs.

**Acceptance Scenarios**:

1. **Given** a pull request that changes `.github/workflows/ci.yml`, **When** CI runs, **Then**
   all jobs run unconditionally, regardless of what else did or did not change in the same PR.

---

### Edge Cases

- What happens when a pull request changes only a file with no matching path rule at all (e.g. a
  new top-level dotfile)? The system defaults to running every job, so an unanticipated path can
  never silently escape coverage.
- What happens on a direct `push` to `main` (post-merge), where the diff may span everything the
  merged PR touched? Path selection applies the same way it did on the pull request; a squash-merge
  push is not treated differently from a PR run today, per this repository's existing convention
  (specs/013-tox-multi-python-testing FR-005/FR-006 already treats them identically).
- What happens to the `performance` job (informational-only, `continue-on-error: true`) and
  `quality-summary` (reporting-only) when their upstream jobs are skipped rather than run? They
  already tolerate `skipped`/`cancelled` results distinctly from `failure` (specs/004-pr-quality-
  check-summary), so a path-driven skip renders using the same existing "⏭️ skipped" / "—" cells,
  not a new state.
- What happens when the `schedule`/`workflow_dispatch` triggers run (weekly `dependency-scan`,
  `sync-agent-integrations`)? These are not pull-request diffs and have no "changed paths" to
  select on; path-based selection applies only to `push`/`pull_request` runs, matching the existing
  `if: github.event_name != 'schedule'` guards already on every job it would touch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST determine, per pull request or push run, which top-level path
  categories were touched (at minimum: Python source/tests/packaging config; documentation source;
  specs and skill/agent-integration files; CI workflow configuration itself).
- **FR-002**: The system MUST run a job only when at least one changed path falls into a category
  that job depends on, except as required by FR-004.
- **FR-003**: The system MUST default to running a job when a changed path matches no known
  category, so an unanticipated file never causes silent under-coverage.
- **FR-004**: The system MUST run every job unconditionally when the change touches the CI
  workflow configuration itself, regardless of what else changed in the same run.
- **FR-005**: The system MUST leave the `ci-ok` aggregate required check reporting success for a
  run in which every one of its dependency jobs either succeeded or was intentionally skipped by
  path selection, and reporting failure when any dependency job that actually ran did not succeed
  — preserving today's guarantee that `ci-ok` is the only check branch protection needs to see.
- **FR-006**: The system MUST leave `schedule`- and `workflow_dispatch`-triggered runs unaffected
  by path selection (`dependency-scan`, `sync-agent-integrations` continue to run on their existing
  triggers, independent of any pull request diff).
- **FR-007**: The system MUST NOT change the pass/fail outcome of any job that does run — path
  selection decides *whether* a job runs, never *how* it evaluates once it runs.
- **FR-008**: The `quality-summary` PR comment MUST continue to render one row per job listed in
  its `needs:`, using its existing status vocabulary, when a job was skipped by path selection
  rather than run.

### Key Entities

- **Path category**: A named group of path globs (e.g. "Python source", "documentation",
  "specs/skills", "CI configuration") that one or more CI jobs depend on. Distinct from a single
  job — several jobs may share a category (e.g. `lint`, `typecheck`, `security`, and `test` all
  depend on "Python source").
- **Job-to-category mapping**: The association from each existing CI job (`lint`, `complexity`,
  `typecheck`, `security`, `test`, `build`, `docs`; `dependency-scan` and `sync-agent-integrations`
  are explicitly out of scope per FR-006) to the path categories that should cause it to run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pull requests that change only non-code paths show the Python-toolchain
  jobs that path has nothing to check reporting as skipped rather than run — docs-only shows
  `lint`/`complexity`/`typecheck`/`security`/`test`/`build` skipped; specs-only shows those six
  plus `docs` skipped; skills-only (`.github/skills/**`/`.claude/**`) shows
  `complexity`/`typecheck`/`security`/`test`/`build`/`docs` skipped but `lint` running (it
  verifies skill symlinks — data-model.md's Path Category Corrections note #4).
- **SC-002**: Every pull request that changes Python source or tests continues to receive exactly
  the same pass/fail verdict from `ci-ok` it would have received before this feature — zero change
  in what blocks a merge for code changes.
- **SC-003**: Zero pull requests merge with an undetected code-quality regression that today's full
  suite would have caught, across the categories this feature reclassifies as skippable.

## Assumptions

- The path categories in FR-001 map onto this repository's existing job set as follows, absent a
  finer-grained need discovered during planning: `lint`/`complexity`/`typecheck`/`security`/`test`/
  `build` depend on Python source (`src/**`, `tests/**`), packaging/config (`pyproject.toml`,
  `tox.ini`), and the two named scripts already referenced by name in those jobs
  (`scripts/sync_agent_integrations.py`, `scripts/setup_skill_symlinks.py`); `docs` additionally
  depends on `docs/**` and any Python source (docstrings feed the Sphinx build).
- `specs/**` and top-level `*.md` files other than `README.md`/`LICENSE.md` are treated as never
  requiring any of the seven filtered jobs on their own. `.github/skills/**`/`.claude/**` and
  `README.md`/`LICENSE.md` were originally assumed to fall in this same "never requires the
  toolchain" set too; Copilot's round-2 review of PR #89 found that false for `lint` (skill
  symlinks) and `build` (packaging metadata) specifically, corrected via the narrower
  `skills`/`packaging_metadata` categories in data-model.md rather than by widening this
  assumption's exceptions — see that document's Path Category Corrections note #4.
- Two tests inside `test` (`test_no_old_package_name.py`, `test_no_old_layout.py`) scan every
  git-tracked file rather than a specific path category, so `test`'s skip is unsound for them
  regardless of which category is involved. Rather than weakening `test`'s skip condition for
  the ~1100 other, genuinely path-scoped tests in that job, they run a second time, unfiltered,
  in a new `repo-invariants` job (also found in the same PR #89 review round).
- This feature changes *trigger conditions* on existing jobs, not their own steps, and adds two
  new jobs (`changes` and `repo-invariants`, both added to `ci-ok`'s `needs:` alongside the
  existing ones) rather than renaming or removing any — the branch protection ruleset (which
  names only `ci-ok`, per issue #75 P2.4) still needs no change, since it never enumerated
  `ci-ok`'s internal dependency list.
- GitHub Actions' own `paths:`/`paths-ignore:` trigger filters are a plausible mechanism but are
  evaluated per-workflow, not per-job, and would prevent the run itself (and therefore `ci-ok`)
  from appearing on an unrelated PR at all, which the branch-protection required-check contract
  does not tolerate (a required check that never reports leaves the PR permanently blocked, per
  `ci-ok`'s own existing comment on this exact failure mode). Choosing between that mechanism and a
  per-job `if:` condition computed from the diff is left to `/speckit-plan`.

## Clarifications

### Session 2026-09-05

- Q: What should SC-001 (the docs/specs-only PR speed-up) actually measure, given this repo's
  Success Criteria convention avoids raw wall-clock numbers? → A: Job-count based — 100% of
  qualifying pull requests show the Python-toolchain jobs as skipped rather than run; no timing
  claim.
