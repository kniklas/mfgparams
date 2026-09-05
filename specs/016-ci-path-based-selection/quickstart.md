# Quickstart: Validating CI Path-Based Job Selection

Prerequisites: this feature's implementation is merged (or pushed to a branch) so
`.github/workflows/ci.yml` includes the `changes` job and the conditional `if:` clauses
described in [data-model.md](./data-model.md) and
[contracts/path-selection-contract.md](./contracts/path-selection-contract.md).

## 1. Static contract checks (fast, run locally, no GitHub Actions run needed)

```bash
pytest tests/static/test_ci_path_selection.py tests/static/test_ci_ok_aggregate_check.py -v
```

Expected: all pass. These encode every MUST in the contract — the per-job category mapping,
the fail-open clause, the CI-config bypass, the excluded-jobs list, and `ci-ok`'s updated
blocking predicate — so a passing run here is the primary acceptance signal for this feature
and MUST be green before any of the live-run checks below are needed.

## 2. US1 — docs/specs-only PR skips the Python toolchain

1. Create a branch from `main`; edit only a file under `specs/**` (e.g. append a sentence to
   this quickstart itself).
2. Open a draft pull request.
3. In the Actions run for that PR, confirm:
   - `changes` ran and succeeded.
   - `lint`, `complexity`, `typecheck`, `security`, `test`, `build` show **Skipped**, not
     Success.
   - `dependency-scan` ran normally (FR-006 — never filtered).
   - `ci-ok` reports **success**.
4. Repeat touching only `docs/source/*.rst` instead; confirm `docs` runs (not skipped) while
   the other six Python-toolchain jobs stay skipped.

**Expected outcome**: matches spec.md US1 Acceptance Scenarios 1-2; SC-001 (100% of such PRs
show the toolchain jobs skipped) is satisfied by this single run generalizing across the
category.

## 3. US2 — a real failure still blocks the merge

1. On a branch touching `src/mfgparams/**`, introduce a deliberate `mypy` violation (e.g. an
   `int` assigned where a `str` is annotated).
2. Open a pull request.
3. Confirm `typecheck` runs and **fails**, and `ci-ok` reports **failure** — identical to
   pre-feature behavior for a code change.
4. On a second branch touching only `specs/**`, confirm `typecheck` shows **Skipped** and
   `ci-ok` still reports **success** (the skip does not block, per the updated predicate in
   data-model.md).

**Expected outcome**: matches spec.md US2 Acceptance Scenarios 1-2.

## 4. US3 — CI config changes always run everything

1. On a branch, edit only `.github/workflows/ci.yml` (e.g. a comment-only change) — nothing
   under `src/**`, `tests/**`, or `docs/**`.
2. Open a pull request.
3. Confirm every filtered job (`lint`, `complexity`, `typecheck`, `security`, `test`, `build`,
   `docs`) runs, not skipped, per FR-004.

**Expected outcome**: matches spec.md US3 Acceptance Scenario 1.

## 5. Fail-open verification (research.md #5) — static only

Triggering a genuine `dorny/paths-filter` action failure in a live run is impractical to stage
safely (it would require pointing the action at an invalid ref or a broken pin on a real PR).
This property is instead verified statically: `tests/static/test_ci_path_selection.py`'s
fail-open assertions (see step 1) parse each filtered job's `if:` string and confirm it
contains both the `needs.changes.result == 'failure'` clause and an explicit status-check
override. Treat a passing run of that test module as sufficient evidence for this scenario —
do not attempt to reproduce the failure live.

## 6. Regression check — mixed-category PR

1. On one branch, touch both a file under `specs/**` and a file under `src/mfgparams/**`.
2. Confirm every job whose category matched runs normally (the Python-toolchain jobs run
   because of the `src/**` change; nothing is skipped that would have run before this
   feature).

**Expected outcome**: matches spec.md US1 Acceptance Scenario 3 — mixed changes never lose
coverage for the code half.

<!-- validation-scratch: mixed diff to exercise T026 regression check -->
