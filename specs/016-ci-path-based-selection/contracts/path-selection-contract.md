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
| `skills` | `.github/skills/**`, `.claude/**` | `lint` only — `setup_skill_symlinks.py --check` is the one toolchain step these paths can break |
| `packaging_metadata` | `README.md`, `LICENSE.md` | `build` only — named as `pyproject.toml`'s `readme`/`license-files`, so these two files are build inputs unlike any other root `*.md` |
| *(none — no job runs for these)* | `specs/**`, root `*.md` other than `README.md`/`LICENSE.md` — the known-non-code paths from spec.md's Assumptions | none of the seven filtered jobs |
| `other` (catch-all) | Anything matching none of the above, **excluding** every row above (including `skills`/`packaging_metadata`, not just the known-non-code row) | all seven filtered jobs (FR-003 — unconditional) |

A path MUST NOT be classified into zero *outputs* being checkable — every path is covered by
either a named triggering category, the known-non-code row, or `other`. A path MAY be
classified into more than one triggering category (e.g. a change that touches both `src/**`
and `docs/**` sets both `python` and `docs` true; both sets of jobs run). `other`'s negation
MUST exclude the known-non-code row's globs as well as `python`/`docs`/`ci_config`'s — a path
already named and deliberately excluded elsewhere in this contract is not "unanticipated," and
folding it into `other` anyway defeats FR-003's actual purpose (never lose coverage for a path
nobody thought about) by making it indistinguishable from "a path this contract already
decided should skip everything." This applies identically to `skills`/`packaging_metadata`:
they are named and handled (by `lint`/`build` respectively), so `other`'s negation excludes
their globs too — unchanged from before these two categories existed, since their globs
(`.github/skills/**`/`.claude/**`/`*.md`) were already in that negation for the "none" row.

**`skills`/`packaging_metadata` do not replace the "none" row** — they narrow it. A
`.github/skills/**` change still runs nothing but `lint`; a `README.md` change still runs
nothing but `build`. Neither triggers `complexity`/`typecheck`/`security`/`test`/`docs`, which
have nothing to check for either path. (Added after Copilot's round-2 review of PR #89 found
the original "none of the seven filtered jobs" claim false for these two path sets — see
data-model.md's Path Category Corrections note #4.)

## `ci-ok` blocking-predicate contract (supersedes the prior "any non-success blocks" rule)

For each job `J` in `ci-ok`'s `needs:` (`changes`, `lint`, `complexity`, `typecheck`,
`security`, `dependency-scan`, `test`, `build`, `docs`, `repo-invariants`):

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

The `changes` job itself MUST also exclude `workflow_dispatch` from its own `if:` (in addition
to `schedule`), not just OR it into the filtered jobs' bypass above. Every filtered job already
ignores `changes`'s outputs on that trigger, so running `changes` for it anyway only gives a
checkout or `paths-filter` failure a way to fail the manual run — for a required `ci-ok`
dependency, that failure blocks the run even though nothing downstream needed its result
(Copilot's round-2 review of PR #89: excluding `workflow_dispatch` from the filtered jobs'
`if:` alone was not sufficient). `tests/static/test_ci_path_selection.py` MUST assert
`changes`'s own `if:` excludes both events.

## Jobs excluded from path selection (FR-006)

`dependency-scan`, `sync-agent-integrations`, `performance`, `quality-summary`, and
`deploy-docs` MUST NOT gain a `needs: [changes]` dependency or any category-based `if:` clause
by this feature. `tests/static/test_ci_path_selection.py` MUST assert none of these five job
names reference `needs.changes` anywhere in their `if:`.

## Repo-wide invariant contract (`repo-invariants`)

`test`'s path-based skip is unsound for any test inside it that scans the whole repository
rather than a specific path category — `tests/static/test_no_old_package_name.py` and
`tests/static/test_no_old_layout.py` both walk every git-tracked file's path and content, so a
violation can appear under `specs/**`, `.github/skills/**`, a root `*.md` file, or `.claude/**`:
every category `test` is allowed to skip for. A `repo-invariants` job MUST run both tests
unconditionally on every non-scheduled trigger (`needs: []`, no category-based `if:` clause),
independent of `changes`, so this gap cannot reopen by `test` being skipped for a path one of
these two tests actually cares about. This is deliberately a second invocation of the same two
tests rather than removing them from `test`'s own run — they are cheap, and duplicating them
costs far less than reworking `test`'s skip condition would (which would have to stop skipping
for virtually every path, defeating SC-001 for the other ~1100 tests in that job). Added in
Copilot's round-2 review of PR #89 (the third HIGH finding of that round).

## Non-goals

- This contract does not change which jobs are named in `ci-ok`'s `needs:` today, except
  adding `changes` (research.md #5) and `repo-invariants` (research.md #8; the Repo-wide
  invariant contract above). No job is renamed, added to, or removed from the set of *quality
  gates* — only these two, neither of which represents a new quality check beyond what `test`
  already ran.
- This contract does not change any job's own steps, tool invocations, or pass/fail logic
  (FR-007) — only the `if:` condition deciding whether those steps run at all.
