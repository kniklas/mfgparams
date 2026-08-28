# Contract: Multi-Python-Version Testing Interface

This is the interface this feature exposes to contributors (the local `tox` command) and to
GitHub branch/ruleset protection (the CI matrix checks) — the same kind of "public API" role
`contracts/ci-checks-contract.md` plays for `003-ci-quality-security-gates`, which this
contract extends rather than replaces.

## Local interface: `tox`

| Command | Behavior |
|---|---|
| `tox` | Runs `pytest --cov=mfgparams --cov-report=term-missing --cov-fail-under=90` once per env in `envlist` (`py39`, `py310`, `py311`, `py312`), each in its own isolated environment with the `dev` extra installed. Exits non-zero if any *available* interpreter's env fails; prints a per-env summary. |
| `tox -e py39` (etc.) | Runs the same suite against a single named version, for a faster inner loop when iterating on one version's failure. |
| Missing interpreter (e.g. no `python3.9` on `PATH`) | That env is reported `SKIPPED` (not `FAILED`, not silently omitted) in the summary; other available envs still run and report their own result; overall exit status reflects only the envs that actually ran (spec.md FR-004). |

## CI interface: `test` matrix checks

Every check below MUST report a distinct, named GitHub Actions check (not bundled into a
single "test" check), extending the same principle `ci-checks-contract.md` established for
the other Principle IX gates.

| Check name | Enforces | Trigger | Blocks merge when |
|---|---|---|---|
| `test (3.9)` | Full suite + coverage on the oldest declared-supported version | push, pull_request | Test failure or coverage below 90% on 3.9 |
| `test (3.10)` | Same, on 3.10 | push, pull_request | Test failure or coverage below 90% on 3.10 |
| `test (3.11)` | Same, on 3.11 — also the canonical leg (`env.PYTHON_VERSION`): the only leg that uploads `coverage.xml` to Codecov, and the only one that writes the `coverage-pct` artifact `quality-summary` renders as the coverage metric. The job exposes no `coverage_pct` job output, because a matrix job's output is published from whichever leg finishes last regardless of which leg set it (research.md #5) | push, pull_request | Test failure or coverage below 90% on 3.11 |
| `test (3.12)` | Same, on the newest declared-supported version | push, pull_request | Test failure or coverage below 90% on 3.12 |

**Note**: `needs.test.result` (consumed by the `quality-summary` job) reflects the matrix
job's aggregate conclusion — it is only `success` if every leg above succeeds — so
`quality-summary`'s existing "test passed/failed" row requires no logic change, only its
underlying gate now covers four versions instead of one.

## Required-status-check update (manual, one-time — resolves spec.md FR-007)

**Status: completed** — see the post-migration state recorded at the end of this section.

Before this feature, `main`'s "status checks" ruleset (created by
`003-ci-quality-security-gates`) required the single check name `test`. Once the matrix ships,
GitHub Actions stops producing that name entirely (a matrixed job only produces per-leg checks)
— so this was not additive, it was a **replacement**:

1. Remove the `test` entry from the ruleset's required-status-checks list.
2. Add all four: `test (3.9)`, `test (3.10)`, `test (3.11)`, `test (3.12)`.
3. Leave every other required check (`lint`, `complexity`, `typecheck`, `security`,
   `dependency-scan`, `build`, `docs`, CodeQL) untouched.

This is a GitHub repository setting, not a version-controlled file, so it cannot be applied by
a code change alone — `tasks.md` tracks it as an explicit, documented step (same pattern
`003-ci-quality-security-gates` used for its own ruleset migration), and it MUST be completed
before/at merge of this feature's PR, otherwise `main` briefly has zero enforced test gate
(the stale `test` entry matches nothing once the workflow changes) rather than the intended
four.

**Post-migration state** (applied during this feature's PR, once its matrix had run once so
GitHub offered the new check names): the `main-required-status-checks` ruleset now requires
`lint`, `complexity`, `typecheck`, `security`, `dependency-scan`, `test (3.9)`, `test (3.10)`,
`test (3.11)`, `test (3.12)`, `build`, `docs`, `Analyze (python)`, and `CodeQL`. The bare `test`
entry is gone; every non-`test` entry is unchanged from before the migration (tasks.md T010).

## Documentation interface: README

The "Run the tests" section MUST, after this feature, let a reader distinguish and follow two
paths without ambiguity:

1. **Single-version** (`pytest`, current default interpreter) — unchanged behavior, plus the
   pip-upgrade prerequisite note (research.md #6) so it actually succeeds on 3.9 as written.
2. **Multi-version** (`tox`) — new; one command to check every supported version locally,
   including how a missing interpreter is reported (table above).
