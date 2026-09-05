---

description: "Task list for 016-ci-path-based-selection"
---

# Tasks: CI Path-Based Job Selection

**Input**: Design documents from `specs/016-ci-path-based-selection/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/path-selection-contract.md, quickstart.md

**Constitution note**: `/speckit-analyze` (2026-09-05) flagged this feature's conditional
skipping of `lint`/`complexity`/`typecheck`/`security`/`test`/`build`/`docs` against
`.specify/memory/constitution.md`'s then-literal "every pull request" language. Resolved by
constitution v1.11.0's "path-based job selection" exception on Principle IX, whose four
safeguards this feature's own design already satisfies (see spec.md Assumptions and
research.md #1-#5); re-confirmed clean by a second `/speckit-analyze` pass the same day.

**Tests**: This feature has no runtime/application code — its entire change surface is
`.github/workflows/ci.yml`'s trigger conditions, verified two ways: static tests that parse
the YAML (the existing repo pattern — see `tests/static/test_ci_ok_aggregate_check.py`) and
the live-PR scenarios in `quickstart.md`, since GitHub Actions `if:`/trigger evaluation cannot
be exercised by running the workflow inside a unit test. Both are included below as explicit
tasks, not optional — `contracts/path-selection-contract.md` states each static assertion as a
MUST, and this repo's Additional Constraints require CI itself to keep passing throughout.

**Organization**: Tasks are grouped by user story (US1 = docs/specs-only PRs skip the Python
toolchain, P1; US2 = a real failure still blocks the merge, P1; US3 = CI-config changes always
run everything, P2) per spec.md priorities, on top of a shared Foundational phase.

**Coupling note**: Unlike a typical feature, the three user stories describe three properties
of the *same* per-job `if:` expression (data-model.md's Job Path Policy table), not three
separable code paths. T008/T009 therefore write each filtered job's complete `if:` string
once, covering all three stories' clauses together — there is no sane way to stage "just the
skip logic" and bolt on the fail-open/CI-config clauses later in the same file without editing
the same line three times. What *is* separable, and what the phases below actually separate,
is verification: each story owns the static-test assertions and quickstart scenario that
prove its specific property, so a reviewer can still confirm US1/US2/US3 independently even
though one edit satisfies all three at once.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow plan.md's Project Structure

---

## Phase 1: Setup

**Purpose**: Establish a known starting point before touching `ci.yml`.

- [X] T001 Confirm branch `016-ci-path-based-selection` is checked out from `main` (already
  true per `/speckit-specify`) — no file edit
- [X] T002 Confirm `dorny/paths-filter`'s current major-version release tag is `v3` (check
  https://github.com/dorny/paths-filter/releases if in doubt) so T003 pins the same
  major-version-tag style this workflow already uses for `actions/checkout@v4`,
  `codecov/codecov-action@v4`, etc. (research.md #1) — no file edit

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Stand up the filter-producer job and the aggregate's updated blocking predicate.
No user story's `if:` wiring can be added until both exist, and the predicate change specifically
must land first — wiring a job to skip before `ci-ok` tolerates `skipped` would make every such
skip immediately block every PR.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 In `.github/workflows/ci.yml`, add a new `changes` job using `dorny/paths-filter@v3`
  (research.md #1), guarded by `if: github.event_name != 'schedule'` (same guard as every job
  it will gate), defining exactly the four named filters and globs from data-model.md's Path
  Category table: `python` (`src/**`, `tests/**`, `pyproject.toml`, `tox.ini`,
  `scripts/sync_agent_integrations.py`, `scripts/setup_skill_symlinks.py`), `docs`
  (`docs/**`), `ci_config` (`.github/workflows/**`), and `other` (a negation glob matching
  anything none of the first three match) (research.md #2). **Superseded by T030/T032** —
  the guard and category set described here are the pre-review design; re-running this task
  from scratch reproduces the two gaps those later tasks fixed.
- [X] T004 In `.github/workflows/ci.yml`, change `ci-ok`'s embedded Python assertion step so
  a dependency's `result` is only added to `failures` when it is not in
  `("success", "skipped")` (currently: not equal to `"success"`), per research.md #3 and
  contracts/path-selection-contract.md's blocking-predicate table
- [X] T005 In `.github/workflows/ci.yml`, add `changes` to `ci-ok`'s `needs:` list
  (research.md #5)
- [X] T006 [P] In `tests/static/test_ci_ok_aggregate_check.py`, add `"changes"` to
  `REQUIRED_JOBS` (research.md #5); run
  `pytest tests/static/test_ci_ok_aggregate_check.py -v` and confirm
  `test_ci_ok_gates_exactly_the_required_jobs` and `test_every_ci_job_is_classified` still pass
- [X] T007 Create `tests/static/test_ci_path_selection.py` (new file, module docstring
  explaining the invariant per this repo's convention in `test_ci_ok_aggregate_check.py`) with
  two initial checks: (a) the `changes` job exists, is guarded by
  `if: github.event_name != 'schedule'`, and defines exactly the four filters/globs from
  data-model.md's Path Category table (contracts/path-selection-contract.md's "Path category
  contract"); (b) `ci-ok`'s assertion step body (parsed the same way
  `test_ci_ok_actually_asserts_its_dependencies` already does) accepts `"success"` and
  `"skipped"` and rejects `"failure"`/`"cancelled"`, per contracts/path-selection-contract.md's
  blocking-predicate table (verifies T004). **Superseded by T030/T032** — the "exactly the
  four filters" and single-event-guard checks in (a) describe the pre-review design; the
  static suite now requires six categories, two `paths-filter` steps, and a `workflow_dispatch`
  exclusion on top of the `schedule` one. Re-running this task as written would delete real
  coverage T030/T032 added.

**Checkpoint**: The filter producer and the aggregate's new predicate both exist and are
tested. No filtered job skips anything yet — that is wired next, per story.

---

## Phase 3: User Story 1 - Docs-only and spec-only changes skip the Python toolchain (Priority: P1) 🎯 MVP

**Goal**: `lint`, `complexity`, `typecheck`, `security`, `test`, `build`, and `docs` run only
when a changed path falls into a category they depend on.

**Independent Test**: quickstart.md §2 — open a PR touching only `specs/**`, confirm those
jobs show Skipped and `ci-ok` still succeeds; repeat touching only `docs/source/**` and confirm
`docs` runs while the rest stay skipped.

### Implementation for User Story 1

- [X] T008 [US1] In `.github/workflows/ci.yml`, add `needs: [changes]` to `lint`, `complexity`,
  `typecheck`, `security`, `test`, and `build`, and change each one's `if:` to (per
  data-model.md's Job Path Policy table):
  `!cancelled() && github.event_name != 'schedule' && (needs.changes.result == 'failure' || needs.changes.outputs.python == 'true' || needs.changes.outputs.ci_config == 'true' || needs.changes.outputs.other == 'true')`
  (research.md #2, #5, #7)
- [X] T009 [US1] In `.github/workflows/ci.yml`, add `needs: [changes]` to `docs` and change its
  `if:` to the same formula as T008 plus `|| needs.changes.outputs.docs == 'true'`
  (data-model.md Job Path Policy; research.md #2)

### Tests for User Story 1

- [X] T010 [US1] In `tests/static/test_ci_path_selection.py`, add assertions that each of the
  six jobs from T008 has `needs` including `"changes"` and an `if:` string containing
  `needs.changes.outputs.python` and `needs.changes.outputs.other` (the relevance-based skip
  and the unmatched-path default, FR-002/FR-003) — deliberately not asserting the
  `ci_config`/fail-open clauses here; those are US3's and US2's own test tasks (T019, T015)
- [X] T011 [US1] In the same file, add an assertion that `docs`'s `if:` additionally contains
  `needs.changes.outputs.docs`
- [X] T012 [US1] In the same file, add an assertion that `quality-summary`'s `needs:` list
  still contains all seven filtered job names (`lint`, `complexity`, `typecheck`, `security`,
  `test`, `build`, `docs`) unchanged, per FR-008 — this guards research.md #4's finding that
  `quality-summary`'s existing `status_label()` function already renders a `skipped` result
  correctly, by keeping that job wired to see the result in the first place (a future edit
  removing a job from `quality-summary`'s `needs:` would silently stop reporting it, which no
  other test in this file would catch)
- [X] T013 [US1] Run `pytest tests/static/test_ci_path_selection.py tests/static/test_ci_ok_aggregate_check.py -v`
  and confirm all pass (quickstart.md §1)

### Validation for User Story 1

- [X] T014 [US1] Perform quickstart.md §2: open a draft PR touching only `specs/**`, confirm
  `lint`/`complexity`/`typecheck`/`security`/`test`/`build` show **Skipped** and `ci-ok`
  reports **success**; repeat touching only `docs/source/*.rst` and confirm `docs` runs while
  the other six stay skipped. While this PR is open, also confirm the `quality-summary` PR
  comment renders a "⏭️ skipped" row for each skipped job rather than omitting it (FR-008).
  **Done via throwaway PRs #90/#91** (closed, branches deleted after observing CI). Caught
  two implementation bugs neither planning nor the static tests surfaced — both now fixed and
  covered by new/extended static-test assertions and recorded in data-model.md's Path
  Category "Corrections" note: (1) `other`'s first negation glob omitted the known-non-code
  paths (`specs/**` etc.), so a specs-only PR matched `other` and ran everything anyway; (2)
  fixing that as a `!(a/**|b/**|...)` extglob string still failed the identical live check —
  a single extglob negation containing `**` in its own alternatives is unreliable; (3) the
  working list form (`**` then per-glob `!` exclusions) *still* matched everything until
  `predicate-quantifier: every` was set on `other`'s own separate `paths-filter` step — the
  default `some` quantifier means the leading bare `**` alone already satisfies the filter,
  making every negation after it moot. All three needed a real GitHub Actions run to surface
  — none were visible from the YAML alone.

**Checkpoint**: User Story 1 is fully functional and independently testable — docs/specs-only
PRs demonstrably skip the toolchain, and `ci-ok` stays green throughout.

---

## Phase 4: User Story 2 - A real failure still blocks the merge (Priority: P1)

**Goal**: A job that runs and genuinely fails still fails `ci-ok`, exactly as today (FR-007); a
broken `changes` job never silently narrows the gate.

**Independent Test**: quickstart.md §3 and §5 — a deliberate `mypy` violation on a
`src/**`-touching PR still fails `ci-ok`; the fail-open clause (already written into every
job's `if:` by T008/T009) is verified statically rather than by staging a live filter-action
failure.

### Tests for User Story 2

- [X] T015 [US2] In `tests/static/test_ci_path_selection.py`, add assertions that every job
  wired in T008/T009 has an `if:` string containing both `needs.changes.result == 'failure'`
  and an explicit status-check override (`!cancelled()`), per
  contracts/path-selection-contract.md's "Fail-open contract for the changes job" — this is
  the test that would fail if a future edit dropped either half of that clause
- [X] T016 [US2] In the same file, add assertions that `dependency-scan`,
  `sync-agent-integrations`, `performance`, `quality-summary`, and `deploy-docs` do **not**
  reference `needs.changes` anywhere in their `if:`, per contracts/path-selection-contract.md's
  "Jobs excluded from path selection" (FR-006)
- [X] T017 [US2] Run `pytest tests/static/test_ci_path_selection.py -v` and confirm T015/T016
  pass alongside US1's assertions

### Validation for User Story 2

- [X] T018 [US2] Perform quickstart.md §3: on a branch touching `src/mfgparams/**`, introduce a
  deliberate `mypy` violation; confirm `typecheck` runs and **fails** and `ci-ok` reports
  **failure** (FR-007 — the job's own pass/fail outcome is unchanged by this feature). On a
  second, `specs/**`-only branch, confirm `typecheck` shows **Skipped** and `ci-ok` still
  reports **success**. On a third branch touching `src/mfgparams/**` with no defects, confirm
  every filtered job passes and `ci-ok` reports **success** exactly as it would have before
  this feature (SC-002's ordinary, all-green case, not just the failing one).
  **Done via throwaway PR #92** for the failure case (`typecheck` failed as intended;
  `lint` also failed, incidentally, on unformatted content the throwaway edit itself
  introduced — a real failure either way, correctly blocking `ci-ok`); the specs-only case
  is the same evidence as T014; the clean-green case is covered by PR #89 (the real feature
  PR) itself passing every python-category job normally.

**Checkpoint**: User Stories 1 and 2 both hold — skips never block, real failures always do,
and a broken filter mechanism fails open rather than silently passing.

---

## Phase 5: User Story 3 - Changes to CI configuration itself are always fully validated (Priority: P2)

**Goal**: A change to `.github/workflows/ci.yml` itself runs every filtered job unconditionally,
regardless of what else did or did not change in the same diff.

**Independent Test**: quickstart.md §4 — a PR editing only `ci.yml` (e.g. a comment) still runs
every filtered job.

### Tests for User Story 3

- [X] T019 [US3] In `tests/static/test_ci_path_selection.py`, add an assertion that all seven
  filtered jobs' (`lint`, `complexity`, `typecheck`, `security`, `test`, `build`, `docs`) `if:`
  strings contain `needs.changes.outputs.ci_config`, per
  contracts/path-selection-contract.md's "CI-config bypass contract" (FR-004)
- [X] T020 [US3] Run `pytest tests/static/test_ci_path_selection.py -v` and confirm T019 passes
  alongside US1's and US2's assertions

### Validation for User Story 3

- [X] T021 [US3] Perform quickstart.md §4: on a branch, edit only `.github/workflows/ci.yml`
  (a comment-only change) with no `src/**`/`tests/**`/`docs/**` changes in the same diff;
  confirm every filtered job runs, none skipped. **Done via PR #89 itself** (this feature's
  own PR touches `ci.yml`, so FR-004 applies to every one of its own CI runs) — every
  filtered job ran and passed on every push to that PR, never skipped, across all four
  rounds of fixes.

**Checkpoint**: All three user stories are independently verified. The feature's core
behavior is complete; remaining work is documentation upkeep and final regression checks.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Fix the documentation that currently states, as fact, semantics this feature
changes (research.md #6), and run the final regression/mixed-diff check.

- [X] T022 [P] Update `specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md`'s
  `ci-ok` row ("Blocks merge when: Any of the eight gating jobs failing, being cancelled, or
  being skipped") to reflect the new predicate (skip is non-blocking; also now nine jobs with
  `changes` added) — research.md #6. **Continued by T033** once `repo-invariants` made it ten.
- [X] T023 [P] Update `.github/skills/code-review/SKILL.md` §7a's description of `ci-ok`
  passing "only when all eight individually succeed" to match the new predicate and job count
  — research.md #6. **Continued by T033** once `repo-invariants` made it ten.
- [X] T024 [P] Update `.github/skills/pr-review-loop/SKILL.md` §5's equivalent description —
  research.md #6. **Continued by T033** once `repo-invariants` made it ten.
- [X] T025 [P] Correct `tests/static/test_ci_ok_aggregate_check.py`'s
  `test_ci_ok_only_excludes_scheduled_runs` docstring: its stated rationale ("the assertion
  step sees 'skipped' and fails") is no longer why `ci-ok` excludes scheduled runs post-T004 —
  the exclusion is now justified purely by "no pull request exists to gate on a schedule run."
  The assertion itself is unchanged; only the comment is wrong after T004
- [X] T026 Perform quickstart.md §6 (mixed-category regression check): on one branch, touch
  both a file under `specs/**` and a file under `src/mfgparams/**`; confirm every job whose
  category matched runs normally and nothing that would have run before this feature is now
  skipped. **Done via throwaway PR #93**: every python-category job ran (none skipped) —
  `lint` failed on unformatted content the throwaway edit itself introduced, correctly
  blocking `ci-ok`, which if anything is stronger evidence than a clean pass would have been.
- [X] T027 Run the full local check suite (`ruff check`, `black --check`, `mypy`, and `pytest`)
  against the two modified/created Python test files
  (`tests/static/test_ci_ok_aggregate_check.py`, `tests/static/test_ci_path_selection.py`) to
  confirm no lint/type regressions before opening the pull request
- [X] T028 Discovered running the *full* suite (not just the two files T027 scoped to):
  `tests/static/test_packaging_marker_still_gates.py::test_the_packaging_step_can_actually_fail_the_build_job`
  pinned `build`'s `if:` to exactly `None` or `"github.event_name != 'schedule'"`, deliberately
  rejecting any other condition as an unreviewed narrowing of wheel verification. T008's new
  condition on `build` is exactly such an "other condition." Fixed by updating that test to
  also accept the path-based condition, but only when it still contains the schedule
  exclusion, the fail-open clause, and the `other` catch-all — preserving the original guard's
  intent (reject anything that could silently narrow verification) rather than loosening it to
  accept any string. Missed during `/speckit-plan`'s Project Structure survey (plan.md did not
  list this file); full suite now at 1100 passed, 10 skipped, matching pre-feature skip count
- [X] T029 Discovered during T014's live PR (#90, a specs-only diff): `other` reported `true`
  for `specs/016-ci-path-based-selection/quickstart.md` despite `specs/**` being named in its
  negation, running every filtered job on the one diff US1 exists to skip it for — a real
  functional bug static tests and `/speckit-analyze` both missed, because both only ever
  checked the glob *text*, never `dorny/paths-filter`'s actual matching behavior. Took two
  more rounds to fix correctly (see data-model.md's Path Category "Corrections" note for the
  full detail): a single `!(a/**|b/**|...)` extglob string is silently unreliable once its
  alternatives contain `**`; the documented list form (`**` then `!`-exclusions) still failed
  under the default `predicate-quantifier: some`, since a bare `**` alone already satisfies
  "some" on its own. Fixed by giving `other` its own `paths-filter` step with
  `predicate-quantifier: every`. `tests/static/test_ci_path_selection.py` gained
  `test_other_filter_step_uses_every_quantifier` specifically so this exact regression - correct
  glob text under the wrong quantifier - fails loudly next time rather than requiring another
  live PR to notice
- [X] T030 Copilot's round-2 review of PR #89 found the four-category design incomplete: two
  known-non-code paths were load-bearing for specific jobs. Added `skills`
  (`.github/skills/**`, `.claude/**` — runs `lint` only, which verifies skill symlinks) and
  `packaging_metadata` (`README.md`, `LICENSE.md` — runs `build` only, which packages them)
  categories in `.github/workflows/ci.yml`, data-model.md, contracts/path-selection-contract.md
  and research.md #2/#4; extended `tests/static/test_ci_path_selection.py` with the matching
  glob/wiring assertions (see data-model.md's Path Category Corrections note #4)
- [X] T031 Same review round found `test`'s path-based skip unsound for
  `tests/static/test_no_old_package_name.py`/`test_no_old_layout.py`, which scan every
  git-tracked file rather than a path category. Added a new, never-filtered `repo-invariants`
  job (research.md #8) that reruns both tests on every non-scheduled trigger, and added it to
  `ci-ok`'s `needs:` and `tests/static/test_ci_ok_aggregate_check.py`'s `REQUIRED_JOBS`
- [X] T032 Same review round also found `changes` itself still ran (and could fail) on
  `workflow_dispatch` even though every filtered job already bypasses its output for that
  trigger. Excluded `workflow_dispatch` from `changes`'s own `if:` too (in addition to
  `schedule`), documented in contracts/path-selection-contract.md's Manual-dispatch bypass
  contract and data-model.md's Job Path Policy `changes` row
- [X] T033 Copilot's round-3 review of PR #89 found T030-T032 had not been propagated
  everywhere T022-T024 originally landed the four-filter/nine-job design, plus one document
  (specs/013-tox-multi-python-testing/spec.md) never covered by T022-T024 at all:
  - `specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md`'s `ci-ok` row:
    nine gating jobs → ten (`repo-invariants`); `changes`'s "never `skipped`" claim corrected
    to "skipped only on `workflow_dispatch`, which every filtered job already tolerates"
  - `.github/skills/code-review/SKILL.md` §7a and `.github/skills/pr-review-loop/SKILL.md` §5:
    same nine → ten correction, plus `pr-review-loop`'s exit-criteria section now explains
    which of the ten jobs are never path-skipped and why
  - `specs/016-ci-path-based-selection/data-model.md`/`research.md`: the `changes`-job
    "never skipped" claim, the four-category table (now six, research.md #2), and decision #5's
    fail-open example now show the `workflow_dispatch` clause alongside the failure clause
  - `specs/016-ci-path-based-selection/spec.md`: User Story 1's prose and SC-001 corrected to
    say a skills-only change runs `lint` (not skipped, per T030) instead of all seven jobs
    skipping
  - `specs/016-ci-path-based-selection/plan.md`: post-design Constitution Check assessment
    updated to name `repo-invariants` and the fuller set of touched documents, not just
    `changes` and three documents
  - `.github/workflows/ci.yml`: the `test` job's matrix comment and `ci-ok`'s own comment
    block both qualified to describe the actual `push`/`pull_request`-vs-`workflow_dispatch`
    behavior instead of the pre-round-2 claims
  - `specs/013-tox-multi-python-testing/spec.md`: FR-005/FR-007/SC-003/SC-004 each gained a
    "Qualified by `specs/016-ci-path-based-selection`" note (kept as historical record, not
    rewritten, matching how `ci-checks-contract.md`'s own `test` row already annotates a prior
    supersession) — `test`'s "on every pull request" guarantee is now conditional on path
  - This task itself and T003/T007/T022-T024 above gained inline "Superseded by"/"Continued
    by" pointers so a future contributor replaying this file from the top lands on the final
    design, not the pre-review one

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (T008/T009 need
  `changes` to exist from T003; every story's skip behavior needs T004's predicate change to
  be non-blocking)
- **User Stories (Phase 3-5)**: All depend on Foundational completion. T008/T009 (US1's
  implementation) also satisfy the `if:`-string prerequisites T015/T016 (US2) and T019 (US3)
  test against — so while US2/US3 are independently *verifiable*, their test tasks depend on
  US1's T008/T009 having already been written, not just on Foundational
- **Polish (Phase 6)**: Depends on all three user stories being complete

### Within Each Phase

- Tasks touching `.github/workflows/ci.yml` (T003-T005, T008-T009) are strictly sequential —
  same file, and each builds on the previous job/step existing
- Tasks touching `tests/static/test_ci_path_selection.py` (T007, T010-T012, T015-T016, T019)
  are strictly sequential once T007 creates the file — same file
- Validation tasks (T014, T018, T021, T026) depend on their phase's implementation and test
  tasks being complete and pushed to a real pull request

### Parallel Opportunities

- T006 (different file: `test_ci_ok_aggregate_check.py`) can run in parallel with T007 (new
  file: `test_ci_path_selection.py`) once T003-T005 land
- T022, T023, T024, T025 (Polish) each touch a distinct file and can all run in parallel

---

## Parallel Example: Foundational

```bash
# Once T003-T005 land, these two touch different files:
Task: "Add 'changes' to REQUIRED_JOBS in tests/static/test_ci_ok_aggregate_check.py"
Task: "Create tests/static/test_ci_path_selection.py with the changes-job and ci-ok-predicate checks"
```

## Parallel Example: Polish

```bash
Task: "Update specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md's ci-ok row"
Task: "Update .github/skills/code-review/SKILL.md §7a"
Task: "Update .github/skills/pr-review-loop/SKILL.md §5"
Task: "Correct test_ci_ok_aggregate_check.py's test_ci_ok_only_excludes_scheduled_runs docstring"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: quickstart.md §2 on a real draft PR
5. This alone delivers the feature's primary value (SC-001) — US2/US3 harden it against two
   specific ways it could go wrong, but a merge after US1 alone is not unsafe, since T004's
   predicate change and T008/T009's fail-open/ci_config clauses are written as one edit, not
   staged — there is no intermediate state where skips are wired but fail-open isn't

### Incremental Delivery

1. Setup + Foundational → filter mechanism exists, aggregate tolerates skips
2. Add US1 → validate independently → this is the MVP
3. Add US2 → validate independently → hardens against filter-mechanism failure and real
   regressions being masked
4. Add US3 → validate independently → closes the last edge case (CI-config changes exempting
   themselves from their own review)
5. Polish → fix documentation that would otherwise silently go stale the moment this merges

### Single-Contributor Reality Check

This repository is single-reviewer (per prior slices' merge notes); there is no parallel-team
strategy to describe here beyond what the Parallel Examples above already capture at the
task level.
