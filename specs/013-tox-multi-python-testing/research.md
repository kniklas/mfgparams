# Research: Verified Multi-Python-Version Local & CI Testing

## #1: Local multi-version test runner

**Decision**: `tox` (added to `[project.optional-dependencies].dev`), configured via a
top-level `tox.ini` with `envlist = py39, py310, py311, py312` and
`skip_missing_interpreters = true`. Each env installs the project's `dev` extra and runs the
identical command CI uses: `pytest --cov=mfgparams --cov-report=term-missing
--cov-fail-under=90`.

**Rationale**:
- Ecosystem-standard for exactly this problem (run the same pytest-based suite against
  several declared interpreters) with minimal, declarative, ini-style config — consistent
  with how every other dev tool in this project is configured (`[tool.ruff]`, `[tool.black]`,
  `[tool.mypy]`, `[tool.pytest.ini_options]` all live as static config, not scripts).
- `skip_missing_interpreters = true` directly satisfies FR-004/Edge Cases: a contributor
  missing one or more supported interpreters gets each missing version clearly reported as
  `SKIPPED` in tox's summary, while available versions still run and report their own
  pass/fail — no manual per-version environment bootstrapping (FR-003), and no silent
  false-pass or hard-crash of the whole run.
- `tox`'s environment creation uses `virtualenv`, whose seeder installs its own current `pip`
  wheel into each created environment independent of the base interpreter's system `pip`.
  This means the exact failure mode hit while validating this repo by hand — a Python 3.9
  install whose bundled `pip` (20.2.3) predates PEP 660 editable-install support — does not
  recur under `tox`, even on the oldest supported interpreter. (It does still apply to the
  plain, non-tox `python -m venv` + `pip install -e ".[dev]"` path documented in the README,
  which is why that path separately needs the pip-upgrade caveat — see #6.)
- Interpreter discovery: `tox`/`virtualenv` looks for `pythonX.Y` on `PATH` by default. Every
  supported version installed via `pyenv` exposes exactly that command as a shim (confirmed:
  `python3.9`, `python3.10`, `python3.11`, `python3.12` all resolve once the corresponding
  `pyenv` version is installed) — no extra discovery plugin needed for the common case of a
  contributor using `pyenv` to hold multiple interpreters.

**Alternatives considered**:
- **`nox`**: More powerful (full Python for session definitions) but that power isn't needed
  here — the requirement is "run one fixed pytest command per supported version," not
  parameterized/branching session logic. Its Python-file config would also be the only
  non-declarative dev-tool config in the project, adding cognitive overhead for no payoff.
- **Hand-rolled shell script looping over interpreters**: Rejected — reimplements interpreter
  discovery, per-env isolation, and missing-interpreter handling that `tox` already provides,
  and wouldn't give contributors a single well-known command (`tox`) to reach for.

## #2: Fixing the `setuptools` dev-extra constraint

**Decision**: Split the existing `setuptools>=83.0.0` line in `[project.optional-dependencies].dev`
by `python_version`, mirroring the pattern already used for `black` in the same extra:

```toml
"setuptools>=83.0.0; python_version >= '3.10'",
"setuptools>=64.0.0,<83.0.0; python_version < '3.10'",
```

**Rationale**:
- `setuptools>=83.0.0` itself declares `Requires-Python >=3.10`, so on a real 3.9 interpreter
  pip cannot find *any* version satisfying `setuptools>=83.0.0`, and the whole `pip install
  -e ".[dev]"` resolution fails before touching any other dependency (reproduced directly:
  `ERROR: Could not find a version that satisfies the requirement setuptools>=83.0.0`).
- `64.0.0` is the first `setuptools` release with full PEP 660 (`build_editable`) support,
  which is the actual functional requirement for `pip install -e ".[dev]"` to work at all —
  so the `<3.10` floor is chosen for a concrete reason, not an arbitrary "something recent."
- The upper bound (`<83.0.0`) on the `<3.10` branch avoids ever attempting to resolve a
  `setuptools` release that has already declared itself incompatible with those interpreters,
  which is the same shape of problem being fixed.
- Minimal-diff: the `>=3.10` branch keeps today's exact constraint (`>=83.0.0`) unchanged, so
  behavior on the versions that currently work (3.10+) is untouched — only the previously-
  broken 3.9 install path is fixed.

**Alternatives considered**:
- **Lower the floor to `setuptools>=64.0.0` for all Python versions**: Rejected — this would
  silently relax the constraint already in place for 3.10+ for no reason connected to this
  feature's scope (spec.md Assumptions: this feature fixes verified-version support, not
  unrelated tooling-version policy), and reviewers of the diff would have no way to tell
  whether the relaxation was intentional.
- **Drop the dev-extra `setuptools` pin entirely and rely on the `[build-system].requires`
  floor (`setuptools>=77`)**: Rejected — `>=77` alone does not guarantee PEP 660 support is
  present (it already is, since 77 > 64, but this stops being obviously true if the
  build-system floor is ever changed independently) and removing the explicit dev pin loses
  the documented, deliberate version reasoning entirely.

## #3: CI matrix strategy for the `test` job

**Decision**: Convert `test` in `.github/workflows/ci.yml` to a matrix job:

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12"]
```

with `python-version: ${{ matrix.python-version }}` in its `actions/setup-python` step. All
four legs run the unchanged `pip install -e ".[dev]"` + `pytest --cov=mfgparams
--cov-report=term-missing --cov-fail-under=90` commands.

**Rationale**:
- `fail-fast: false` is required by spec.md User Story 3 Acceptance Scenario 2: a failure
  specific to one version must be identifiable while the *other* versions still report their
  own independent pass/fail — the default `fail-fast: true` would cancel in-flight legs on
  the first failure, hiding whether the change would have passed on the others.
- A native GitHub Actions matrix (rather than routing CI through `tox`) keeps the `test` job
  structurally identical to every other job in this workflow (`lint`, `typecheck`, `security`,
  etc. — checkout, setup-python, `pip install -e ".[dev]"`, run command) with only the
  `python-version` input varying. This is the smallest change that satisfies FR-005/FR-006,
  and keeps `tox` scoped to its actual purpose (the local workflow, #1) rather than becoming
  an indirection layer inside CI that every other job doesn't use.
- Each matrix leg surfaces as a distinctly named GitHub check (`test (3.9)`, `test (3.10)`,
  `test (3.11)`, `test (3.12)`), directly satisfying FR-006's "distinct, individually
  attributable result per Python version."

**Alternatives considered**:
- **Route CI's `test` job through `tox` (e.g., via `tox-gh-actions`)**: Rejected — adds a
  dependency and an extra layer of indirection (tox environment resolution inside a CI
  runner that already provides exactly one interpreter per job via `setup-python`) for no
  behavioral benefit over a native matrix, and would make `test` the only job in this
  workflow not following the plain checkout → setup-python → install → run shape.
- **Keep `test` single-version in CI, rely on `tox` running locally/pre-push**: Rejected per
  the user's explicit decision (this repo's maintainer chose the full-matrix option) —
  verification would still depend on contributor diligence rather than being guaranteed on
  every pull request (spec.md FR-005, SC-003).

## #4: `tox.ini` command parity with CI

**Decision**: `tox.ini`'s `[testenv]` `commands` runs the byte-identical pytest invocation
CI's `test` job uses (`pytest --cov=mfgparams --cov-report=term-missing --cov-fail-under=90`),
sourced from the project's `[tool.pytest.ini_options].addopts` (already set to this exact
string, so `tox.ini` can invoke plain `pytest` and inherit it, rather than re-stating the
flags) — with `extras = dev` so each tox-managed environment gets the same dependency set
`pip install -e ".[dev]"` provides.

**Rationale**: Avoids two independently-maintained copies of the same test command drifting
apart over time (e.g., someone updates CI's coverage threshold and forgets `tox.ini`, or vice
versa) — the single source of truth stays `pyproject.toml`'s `addopts`, and both CI and `tox`
simply invoke `pytest`.

**Alternatives considered**: Duplicating the full flag list explicitly in `tox.ini` for
"clarity" — rejected, since it reintroduces exactly the drift risk this decision avoids, and
`addopts` is already the documented, single source of truth for the test invocation (README's
existing "Run the tests" section relies on the same mechanism today).

## #5: Keeping `quality-summary`'s single-value coverage output correct, and restricting the Codecov upload

**Decision** (as first implemented, corrected after a `/code-review` finding — see below): gate
only the Codecov-upload step behind `if: matrix.python-version == env.PYTHON_VERSION` (the
version every other CI job already pins). The `coverage_pct` job-output step runs
**unconditionally on every leg**.

**Original (incorrect) decision**: the first implementation gated *both* the Codecov upload and
the `coverage_pct` step behind `if: matrix.python-version == '3.11'`, reasoning that pinning the
job output's source to one leg would keep it deterministic.

**Why that was wrong**: a GitHub Actions matrix job's `output` is published from whichever leg's
job instance *completes last*, not from whichever leg actually set a non-empty value. Gating the
`coverage` step meant three of the four legs never ran it at all, so
`steps.coverage.outputs.coverage_pct` was empty in their context — if one of those legs happened
to finish last (a real possibility with `fail-fast: false` and four independently-racing legs),
`needs.test.outputs.coverage_pct` resolved to an empty string, and `quality-summary`'s
`TEST_METRIC` would intermittently go missing with no job failing to flag it. This was caught by
a `/code-review` pass on the open PR (specs/013-tox-multi-python-testing), not before merge.

**Corrected rationale**: removing the `if:` gate from the `coverage` step means every leg
computes and sets `coverage_pct` from its own `.coverage` data. Coverage percentage is a
property of the code under test, not the interpreter running it (this suite has no
version-conditional test skips that would change line-coverage counts), so every leg's value is
expected to be numerically identical — meaning it no longer matters which leg "wins" the
race, because every candidate value is correct. The Codecov-upload step stays restricted to the
canonical leg, since that's a real per-leg side effect (an HTTP upload) where redundancy is
worth avoiding, unlike a job output. The canonical-leg comparison itself was also changed from
the literal `'3.11'` to `env.PYTHON_VERSION`, so it can never independently drift from the one
declared canonical version (a second `/code-review` finding on the same PR) — and
`tests/static/test_python_version_consistency.py` gained a third check asserting
`env.PYTHON_VERSION` is always a member of the supported-version set, so dropping it from the
matrix without updating `PYTHON_VERSION` (or vice versa) now fails a test instead of silently
leaving the Codecov-upload `if:` permanently false.

**Alternatives considered**: Aggregating four coverage reports into one — rejected as
unnecessary complexity when the underlying numbers are expected to be identical across
interpreters. A separate, non-matrixed job that downloads the canonical leg's coverage artifact
and republishes it as a single output — rejected as needless indirection once the simpler fix
(just let every leg compute the same value) closes the actual race condition.

## #6: Documenting the pip-upgrade prerequisite

**Decision**: README's "Run the tests" section (and the "Install (development)" section
immediately above it) gains a short, explicit step recommending `python -m pip install
--upgrade pip` (or noting a minimum `pip` version, e.g. ≥21.3) immediately after creating the
virtual environment and before `pip install -e ".[dev]"`, plus a pointer to `tox` for checking
other Python versions locally.

**Rationale**: Directly reproduced while validating this repo by hand: a fresh `python3.9 -m
venv` on this machine shipped `pip 20.2.3`, which predates PEP 660 editable-install support
and fails with `File "setup.py" not found... editable mode currently requires a setup.py
based build` — a genuinely confusing error for a `pyproject.toml`-only, PEP 517/518 project,
with no indication that the fix is "upgrade pip." This satisfies FR-002/FR-009: the documented
steps must lead to success on the oldest supported version *as written*, including whatever
prerequisite that requires. (`tox`-driven runs don't need this callout — see #1 — so it's
scoped to the plain venv+pip instructions specifically.)

**Alternatives considered**: Silently relying on contributors to figure out the pip-upgrade
fix themselves (the status quo) — rejected, since it's exactly the undocumented-troubleshooting
gap SC-001 requires closing.

## #7: Automated safeguard for the supported-version list staying in sync

**Decision**: Add a small committed static test,
`tests/static/test_python_version_consistency.py`, that parses `pyproject.toml`'s
`requires-python`/classifiers, `tox.ini`'s `envlist`, and `ci.yml`'s `test` job's
`matrix.python-version`, and asserts all three enumerate the identical set of Python versions.
It runs as part of the default `pytest` suite (no opt-in flag needed), so it participates in
CI's own `test` job like any other test.

**Rationale**: FR-008 requires the local and CI version sets to "be kept in sync if that range
changes" — a standing, forward-looking guarantee, not a one-time fact true only at the moment
this feature ships. Without an automated check, a future contributor who bumps
`requires-python` (or adds/drops a classifier) has no signal that `tox.ini`/`ci.yml` also need
updating, silently reintroducing the exact "claimed support isn't actually verified" gap this
feature exists to close (spec.md Edge Cases, third bullet). This repo has direct precedent for
exactly this shape of fix: `012-rename-package-mfgparams` closed its own analogous
"don't silently regress" requirement (FR-008 there) with a committed static test
(`tests/static/test_no_old_package_name.py`) rather than a one-off manual check, and this
decision follows the same pattern.

**Alternatives considered**:
- **One-time manual cross-check only** (the original plan): satisfies FR-008 at the moment
  this feature ships but not afterward — rejected as insufficient for a requirement explicitly
  phrased as an ongoing "MUST be kept in sync," per `/speckit-analyze` finding C1.
- **CI-only check (a workflow step, not a pytest test)**: would catch drift in CI but not when
  running the suite locally via `tox`/`pytest`, and would be the only version-consistency
  check in this project not expressed as a `tests/` file — rejected in favor of a plain static
  test, consistent with how `012` solved the same shape of problem.
