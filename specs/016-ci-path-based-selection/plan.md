# Implementation Plan: CI Path-Based Job Selection

**Branch**: `016-ci-path-based-selection` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/016-ci-path-based-selection/spec.md`

## Summary

`.github/workflows/ci.yml` runs its full Python-toolchain job set (`lint`, `complexity`,
`typecheck`, `security`, `test`, `build`, `docs`) on every pull request regardless of what
changed, so a spec-only or docs-only PR pays for a Sphinx build, four `test` matrix legs, and
five other jobs that cannot plausibly have been affected. This feature adds a `changes` job
(using `dorny/paths-filter`, pinned) that classifies the diff into path categories, and makes
each of those seven jobs conditional on the category(ies) it depends on, while leaving
`dependency-scan` and the schedule/`workflow_dispatch`-only jobs untouched (FR-006). The
`ci-ok` aggregate's pass/fail predicate changes from "every dependency succeeded" to "every
dependency succeeded or was intentionally skipped by path selection" (FR-005), and every
filtered job's `if:` is written to fail open — running anyway — if the `changes` job itself
fails, so a broken filter can never silently narrow the merge gate.

## Technical Context

**Language/Version**: GitHub Actions workflow YAML (`.github/workflows/ci.yml`); the assertion
step inside `ci-ok` is embedded Python 3 (already the case today), run via `python3 - <<'PY'`
inline, no new interpreter requirement.

**Primary Dependencies**: `dorny/paths-filter` (a new pinned third-party GitHub Action,
consistent with this workflow's existing use of pinned third-party actions —
`actions/checkout`, `codecov/codecov-action`, `marocchino/sticky-pull-request-comment`,
`peter-evans/create-pull-request`, `actions/deploy-pages`).

**Storage**: N/A.

**Testing**: `pytest` against `tests/static/*.py`, which parse `ci.yml` with `pyyaml` and assert
structural invariants (the existing pattern in `tests/static/test_ci_ok_aggregate_check.py`).
This feature extends that pattern with a new static test module rather than a runtime test,
since GitHub Actions trigger/`if:` logic cannot be exercised by running the workflow in unit
tests.

**Target Platform**: GitHub Actions, `ubuntu-latest` runners — unchanged.

**Project Type**: CI/infrastructure configuration change to an existing library project; no
`src/mfgparams` runtime code is touched.

**Performance Goals**: N/A — SC-001 is job-count based per the 2026-09-05 clarification, not a
timing target.

**Constraints**: MUST preserve the `ci-ok` required-check contract (Constitution Principle IX:
"an aggregate MUST NOT quietly enlarge or shrink the gate, and its composition MUST be enforced
by an automated check") and MUST NOT introduce a path where a broken filter mechanism silently
skips a job that should have run (the "decorative guard" failure mode `code-review/SKILL.md`
§7a already bands CRITICAL for a different case).

**Scale/Scope**: One workflow file (`ci.yml`, ~690 lines today), one existing static test file,
one new static test file, and documentation cross-references in `specs/003`'s contract and two
`.github/skills/*` files that currently state the pre-existing "skip = block" semantics as fact.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle IX (Automated Code Quality, Complexity & Security Gates)**: This feature's entire
  purpose is changing *when* Principle IX's gates run, never *whether* they gate `main`. FR-007
  ("MUST NOT change the pass/fail outcome of any job that does run") and FR-004 (CI-config
  changes always run everything) are the spec-level commitments that keep this compliant. The
  aggregate-composition requirement ("MUST NOT quietly enlarge or shrink the gate... enforced by
  an automated check") is satisfied by extending, not relaxing, `tests/static/
  test_ci_ok_aggregate_check.py` — see Phase 1 design. **Gate: PASS.**
- **Principle V (Resource-Constrained Compatibility)**: N/A — this feature changes CI trigger
  conditions, not runtime code subject to the legacy-hardware budget.
- **Principle VI (Extensibility by Design)**: N/A — no calculation logic touched.
- **Other principles** (I-IV, VII, VIII, X-XII): N/A to a CI-trigger-only change; no new Python
  source, no packaging/versioning change, no user-facing message, no license change, no
  multi-PR-sized branch (this is a single, ordinarily-sized PR like 014/015).

No violations requiring justification. **Constitution Check: PASS** (re-confirmed post-design
below).

## Project Structure

### Documentation (this feature)

```text
specs/016-ci-path-based-selection/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── path-selection-contract.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created here)
```

### Source Code (repository root)

```text
.github/
└── workflows/
    └── ci.yml                              # MODIFIED: new `changes` job + conditional `if:`
                                             # on lint/complexity/typecheck/security/test/
                                             # build/docs; ci-ok's assertion predicate changed

tests/
└── static/
    ├── test_ci_ok_aggregate_check.py       # MODIFIED: `changes` added to REQUIRED_JOBS;
                                             # docstring on the schedule-exclusion test updated
                                             # (its stated rationale changes, not its assertion)
    └── test_ci_path_selection.py           # NEW: category→glob mapping, per-job `if:` wiring,
                                             # catch-all default, CI-config bypass, fail-open
                                             # behavior on `changes` job failure

specs/003-ci-quality-security-gates/
└── contracts/
    └── ci-checks-contract.md               # MODIFIED: `ci-ok` row's "blocks merge when" text
                                             # no longer says a skip always blocks

.github/skills/
├── code-review/SKILL.md                    # MODIFIED: §7a's "eight" job count / semantics
└── pr-review-loop/SKILL.md                 # MODIFIED: same "eight...succeed" description
```

No `src/mfgparams/**` or `docs/source/**` changes. This feature has no runtime code, so there is
no "Option 1/2/3" project-type structure to choose between — the change surface is entirely CI
configuration, its static test coverage, and documentation cross-references that would otherwise
go stale the moment `ci-ok`'s semantics change underneath them.

**Structure Decision**: Single-file workflow change plus static tests, matching how `ci-ok`
itself was introduced in #79 (issue #75 P2.4) — no new workflow file, no separate reusable
action, consistent with this being a modification of existing CI behavior rather than a new
capability needing its own infrastructure.

## Constitution Check (post-design re-check)

Phase 1 design (data-model.md, contracts/path-selection-contract.md) introduces one new job
(`changes`) and one new static test file, and modifies `ci-ok`'s assertion predicate plus three
existing documents. None of this adds runtime code, changes a public API, or touches
calculation logic — the Phase 0 analysis above still holds. **Gate: PASS, unchanged.**

**Post-review update (Copilot's review of PR #89):** the final design additionally introduces
a second new job, `repo-invariants` (research.md #8), and the `skills`/`packaging_metadata`
path categories (research.md #2), plus corrections to several more existing documents than the
three anticipated above (specs/003's contract, both `.github/skills/*.md` operative docs,
specs/013's spec.md, and this feature's own tasks.md) — see data-model.md's Path Category
Corrections note #4 and research.md #6/#8 for what each addresses and why. Still no runtime
code, public API, or calculation-logic change. **Gate: PASS, unchanged.**

## Complexity Tracking

*No Constitution Check violations — this section is not needed.*
