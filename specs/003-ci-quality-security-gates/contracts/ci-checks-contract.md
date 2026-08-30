# Contract: Required CI Status Checks on `main`

This is the interface the CI workflows expose to GitHub branch/ruleset protection and to
contributors reading pull request check results. It is the "public API" of this feature, in
the same sense `contracts/library-api.md` is for `001-metal-drilling-calc`.

## Required status checks

Every check below MUST report a distinct, named GitHub Actions job status (not bundled into
a single opaque "CI" check), so FR-001-FR-006 and SC-004 ("identify exactly which metric or
finding failed") are satisfiable from the PR's checks list alone.

| Check name (job) | Enforces | Trigger | Blocks merge when |
|---|---|---|---|
| `lint` | Existing ruff + black formatting/style, now including FR-001 (`ruff C90` cyclomatic complexity) | push, pull_request | Any lint/format violation or function exceeding the configured complexity threshold |
| `complexity` | FR-002 (`radon mi` via `scripts/check_maintainability.py`, Maintainability Index) — FR-001 (`ruff C90`, cyclomatic complexity) is enforced by the `lint` job below, not duplicated here; note `xenon` was found during implementation to only enforce cyclomatic complexity, not MI, and was dropped (research.md #2) | push, pull_request | Any module exceeds the configured Maintainability Index threshold (research.md #2) |
| `typecheck` | FR-003 (`mypy`) | push, pull_request | Any new/changed type error in `src/machine_calc` |
| `security` | FR-004 (`bandit`) | push, pull_request | Any open high/medium-severity finding without a Suppression Record |
| `dependency-scan` | FR-005 (`pip-audit`) | push, pull_request, schedule (weekly) | Any known CVE in resolved dependencies without a documented risk acceptance |
| ~~`test`~~ **— superseded by `013-tox-multi-python-testing`** | Existing pytest + coverage (≥90% threshold unchanged); now also exports `coverage.xml` (`--cov-report=xml`) and uploads it via `codecov/codecov-action@v4` so `README.md`'s coverage badge (Constitution Principle VII, Phase 9) stays auto-updating | push, pull_request | Any test failure or coverage below threshold (the Codecov upload step is non-blocking: `fail_ci_if_error: false`) |
| `test (3.9)`, `test (3.10)`, `test (3.11)`, `test (3.12)` | **Replaces the single `test` row above.** `013-tox-multi-python-testing` converted this job into a `fail-fast: false` matrix over every supported interpreter, so GitHub no longer produces a check named `test` at all; each version reports independently and all four are required in `main`'s ruleset. The Codecov upload is now restricted to the canonical `env.PYTHON_VERSION` leg. See `specs/013-tox-multi-python-testing/contracts/multi-version-testing-contract.md` for the authoritative version of this row | push, pull_request | Any test failure or coverage below threshold on that specific interpreter |
| `build` | Existing package build check (unchanged) | push, pull_request | Build failure |
| `docs` | Existing Sphinx docs build (unchanged) | push, pull_request | Docs build failure |
| CodeQL default setup (`Analyze (python)` + `CodeQL` check contexts) | FR-006 | push to `main`, pull_request (GitHub-managed, not a custom job) | New high-confidence alert (per GitHub's own gating, not a custom workflow step); both contexts are required in `main`'s status-checks ruleset (T023/T035/T037) |
| `ci-ok` | **Aggregates every row above except the CodeQL contexts.** Issue #75 P2.4: `main`'s ruleset named all 11 workflow jobs individually, so each rename or matrix change had to be mirrored into the ruleset and into 12 committed files — #71's `test` → `test (3.9)`…`test (3.12)` rename took three commits and still missed `.github/pull_request_template.md`. `ci-ok` `needs:` the eight gating jobs and asserts each result explicitly (`if: always()` does not fail a job implicitly, so an unasserted aggregate reports green while `lint` is red). `performance`, `quality-summary`, `deploy-docs` and `sync-agent-integrations` are deliberately excluded, enforced by `tests/static/test_ci_ok_aggregate_check.py` | push, pull_request | Any of the eight gating jobs failing, being cancelled, or being skipped |

**Ruleset status (supersedes the "required in `main`'s ruleset" claims in
the rows above).** Since #79, `main`'s status-checks ruleset requires
exactly three contexts: **`ci-ok`, `Analyze (python)`, `CodeQL`.** Every
other job in this table still runs and still reports under its own name;
those names are simply no longer read by branch protection. Adding a
Python version or renaming a job therefore no longer requires a ruleset
change — which is the whole point of the row above.

**Note**: `lint`, `test`, `build`, `docs` already exist as planned (unimplemented) tasks from
`001-metal-drilling-calc` tasks.md (T037); this feature's plan/tasks extend that same
workflow file rather than duplicating it, adding the `complexity`, `typecheck`,
`security`, and `dependency-scan` jobs alongside them.

## Ruleset bypass contract (resolves FR-008)

- `main` is protected by **two separate GitHub repository rulesets** (not one), because
  GitHub's `bypass_actors` field is scoped to the ruleset as a whole, not to individual rules
  within it (confirmed empirically in T022a) — a bypass entry on one rule would otherwise
  exempt the same actor from every other rule sharing that ruleset.
  1. **"PR review" ruleset**: contains only the "Require a pull request before merging" rule.
     MAY have a bypass entry for the repository owner (actor-scoped, `bypass_mode:
     pull_request`).
  2. **"status checks" ruleset**: contains only the `required_status_checks` rule, listing
     every check in the table above (including CodeQL). MUST NOT have a bypass entry for any
     actor. A failing `complexity`, `typecheck`, `security`, `dependency-scan`, `lint`,
     `test`, `build`, `docs`, or CodeQL check blocks merge for every actor, including the
     repository owner — the PR-review ruleset's bypass has no effect on this ruleset.

## Suppression contract (resolves FR-009)

A finding MAY be suppressed only via a tool-native, in-repo mechanism visible in the diff:

- `bandit`: inline `# nosec` comment with a trailing rationale comment on the same or
  preceding line, or a named test-ID skip in `[tool.bandit]` in `pyproject.toml` with a
  comment above it explaining why.
- `ruff` (`C90`)/`mypy`: `# noqa: C901` / `# type: ignore[<code>]` inline, each with a
  trailing rationale comment.
- `pip-audit`: a documented entry in `pyproject.toml` (or an equivalent ignore file) naming
  the CVE ID and the risk-acceptance rationale, per Suppression Record (data-model.md).

A CI-only suppression (e.g., disabling a check in the workflow YAML, or an ignore rule not
visible in the affected file/config) does not satisfy this contract and MUST be rejected in
review (spec.md User Story 3, Acceptance Scenario 2).
