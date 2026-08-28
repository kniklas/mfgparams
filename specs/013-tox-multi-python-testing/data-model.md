# Data Model: Verified Multi-Python-Version Local & CI Testing

This feature is packaging-metadata, dev-tooling, and CI configuration — it has no runtime
persistence layer, database, or API payload schema, and introduces no application data. The
"entities" below are conceptual records that live in version-controlled configuration and CI
output, not in application code or storage.

## Supported Version Range

The set of Python versions the project commits to supporting, and that must be installable,
locally testable, and CI-verified together.

| Field | Type | Description |
|---|---|---|
| `versions` | list of strings | `["3.9", "3.10", "3.11", "3.12"]` — sourced from `pyproject.toml`'s `requires-python`/`classifiers` (single source of truth; unchanged by this feature) |
| `canonical_version` | string | `"3.11"` — declared once as `env.PYTHON_VERSION`. Every non-matrixed CI job (lint, typecheck, security, etc.) pins it, and inside the `test` matrix it selects the single leg that uploads to Codecov and that publishes the `coverage-pct` artifact `quality-summary` renders (research.md #5) |

**Validation rules**:
- `tox.ini`'s `envlist` and the CI `test` job's `matrix.python-version` MUST both equal
  `versions` — a mismatch between either and `pyproject.toml`'s declared range silently
  reintroduces the unverified-claim gap this feature closes (spec.md Edge Cases). This rule is
  enforced automatically, on every test run, by
  `tests/static/test_python_version_consistency.py` (research.md #7) — not just checked once
  during this feature's own implementation.
- `canonical_version` MUST be a member of `versions`.

## Version Test Result

Represents one Python version's outcome from a single local (`tox`) or CI (matrix leg) run.

| Field | Type | Description |
|---|---|---|
| `python_version` | string | Which of `versions` this result is for |
| `source` | enum | `local-tox` or `ci-matrix` |
| `outcome` | enum | `passed`, `failed`, `skipped-missing-interpreter` (local-only; FR-004) |
| `coverage_pct` | number \| null | Present when `outcome = passed`/`failed`. **Not** identical across versions: `config.py` and `registry_config.py` each carry an interpreter-conditional `tomllib`/`tomli` import fallback, so 3.9/3.10 cover two lines 3.11+ never execute (98.88% vs 98.59% as measured). Only `canonical_version`'s value is published as the repository-level headline metric, via the `coverage-pct` artifact (research.md #5) |

**Validation rules**:
- `outcome = skipped-missing-interpreter` MUST NOT be reported as `passed` (FR-004) and MUST
  NOT, by itself, cause the overall local run's exit status to fail solely because of the
  absence (`tox.ini`'s `skip_missing_interpreters = true`, research.md #1).
- A pull request MUST NOT be mergeable while any `ci-matrix` result has `outcome = failed`
  (FR-007), enforced via the branch-protection ruleset naming every matrix leg individually
  (see `contracts/multi-version-testing-contract.md`).
