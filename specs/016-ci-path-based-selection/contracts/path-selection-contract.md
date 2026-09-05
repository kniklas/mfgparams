# Contract: CI Path-Based Job Selection

This is the interface this feature exposes to contributors reading pull request check
results and to future changes to `.github/workflows/ci.yml`, in the same spirit
`specs/003-ci-quality-security-gates/contracts/ci-checks-contract.md` documents the required
status checks themselves. That contract's `ci-ok` row is updated by this feature (see
research.md #6) — this document is the authoritative detail behind that update.

## Path category contract

Every changed path in a `pull_request`/`push` run MUST be classified into at least one of:

| Category | Matches | Runs when true (in addition to always-on jobs) |
|---|---|---|
| `python` | `src/**`, `tests/**`, `pyproject.toml`, `tox.ini`, `scripts/sync_agent_integrations.py`, `scripts/setup_skill_symlinks.py` | `lint`, `complexity`, `typecheck`, `security`, `test`, `build`, `docs` |
| `docs` | `docs/**` | `docs` |
| `ci_config` | `.github/workflows/**` | all seven filtered jobs (FR-004 — unconditional) |
| *(none — no job runs for these)* | `specs/**`, `.github/skills/**`, root `*.md`, `.claude/**` — the known-non-code paths from spec.md's Assumptions | none of the seven filtered jobs |
| `other` (catch-all) | Anything matching none of the above, **excluding** the known-non-code row above | all seven filtered jobs (FR-003 — unconditional) |

A path MUST NOT be classified into zero *outputs* being checkable — every path is covered by
either a named triggering category, the known-non-code row, or `other`. A path MAY be
classified into more than one triggering category (e.g. a change that touches both `src/**`
and `docs/**` sets both `python` and `docs` true; both sets of jobs run). `other`'s negation
MUST exclude the known-non-code row's globs as well as `python`/`docs`/`ci_config`'s — a path
already named and deliberately excluded elsewhere in this contract is not "unanticipated," and
folding it into `other` anyway defeats FR-003's actual purpose (never lose coverage for a path
nobody thought about) by making it indistinguishable from "a path this contract already
decided should skip everything."

## `ci-ok` blocking-predicate contract (supersedes the prior "any non-success blocks" rule)

For each job `J` in `ci-ok`'s `needs:` (`changes`, `lint`, `complexity`, `typecheck`,
`security`, `dependency-scan`, `test`, `build`, `docs`):

| `J`'s result | Blocks `ci-ok` |
|---|---|
| `success` | No |
| `skipped` | No |
| `failure` | Yes |
| `cancelled` | Yes |

This MUST be enforced by `tests/static/test_ci_path_selection.py` reading the literal
assertion predicate out of `ci-ok`'s step body (the same technique
`test_ci_ok_aggregate_check.py` already uses for `sys.exit(1)`/`NEEDS_JSON`), not merely
asserted in prose — a predicate that silently reverts to "any non-success blocks" would
re-break every path-filtered PR the moment someone "simplifies" that step.

## Fail-open contract for the `changes` job

Every filtered job's `if:` MUST evaluate to `true` (causing the job to run) whenever
`needs.changes.result == 'failure'`, regardless of that job's category outputs. Concretely,
every filtered job's `if:` MUST contain `!cancelled()` (or an equivalent explicit override of
GitHub Actions' implicit `success()`-gating on its `needs:`) — its absence would make the job
silently skip whenever `changes` fails, independent of what the rest of the expression says.

`tests/static/test_ci_path_selection.py` MUST assert, per filtered job, that its `if:` string
contains both `needs.changes.result == 'failure'` (or equivalent) and an explicit status-check
override (`!cancelled()`, `always()`, or `failure()`) — the two halves of this contract only
work together; asserting one without the other would pass a workflow where the override exists
but the fail-open clause was dropped, or vice versa.

## CI-config bypass contract (FR-004)

Every filtered job's `if:` MUST OR in `needs.changes.outputs.ci_config == 'true'` such that a
change touching `.github/workflows/**` runs every filtered job regardless of any other path in
the same diff. `tests/static/test_ci_path_selection.py` MUST assert this per filtered job.

## Manual-dispatch bypass contract (FR-006)

Every filtered job's `if:` MUST OR in `github.event_name == 'workflow_dispatch'`, so a manually
dispatched run is unaffected by path selection regardless of what `changes` classified —
matching that job's pre-016 behavior for this trigger. This is a second, independent
unconditional-run clause alongside the fail-open contract's `needs.changes.result ==
'failure'` above (research.md decision #5's example shows both together in one `if:`, since
GitHub Actions has no way to compose two separate `if:` conditions on one job).
`tests/static/test_ci_path_selection.py` MUST assert this per filtered job.

## Jobs excluded from path selection (FR-006)

`dependency-scan`, `sync-agent-integrations`, `performance`, `quality-summary`, and
`deploy-docs` MUST NOT gain a `needs: [changes]` dependency or any category-based `if:` clause
by this feature. `tests/static/test_ci_path_selection.py` MUST assert none of these five job
names reference `needs.changes` anywhere in their `if:`.

## Non-goals

- This contract does not change which jobs are named in `ci-ok`'s `needs:` today, except
  adding `changes` itself (research.md #5). No job is renamed, added to, or removed from the
  set of *quality gates* — only `changes`, a filter producer, is newly required.
- This contract does not change any job's own steps, tool invocations, or pass/fail logic
  (FR-007) — only the `if:` condition deciding whether those steps run at all.
