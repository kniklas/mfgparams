# Research: Verified Multi-Python-Version Local & CI Testing

## #1: Local multi-version test runner

**Decision**: `tox` (added to `[project.optional-dependencies].dev`), configured via a
top-level `tox.ini` with `envlist = py39, py310, py311, py312` and
`skip_missing_interpreters = true`. Each env installs the project's narrow `test` extra (see
#4) and runs a bare `pytest`, inheriting the coverage flags CI inherits too from
`[tool.pytest.ini_options].addopts`: `--cov=mfgparams --cov-report=term-missing
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
"setuptools>=78.1.1,<83.0.0; python_version < '3.10'",
```

**The `<3.10` floor was raised from `64.0.0` to `78.1.1` after a code review**, for a security
reason rather than a functional one — see "Choosing the `<3.10` floor" below.

**Rationale**:
- `setuptools>=83.0.0` itself declares `Requires-Python >=3.10`, so on a real 3.9 interpreter
  pip cannot find *any* version satisfying `setuptools>=83.0.0`, and the whole `pip install
  -e ".[dev]"` resolution fails before touching any other dependency (reproduced directly:
  `ERROR: Could not find a version that satisfies the requirement setuptools>=83.0.0`).
- **Choosing the `<3.10` floor.** `64.0.0` is the first `setuptools` release with full PEP 660
  (`build_editable`) support, which is the functional requirement for `pip install -e ".[dev]"`
  to work at all — and it was the floor as first implemented. It was raised to `78.1.1` after a
  code review found the range is *never CVE-scanned*: `dependency-scan` runs `pip-audit`
  against an environment built on `env.PYTHON_VERSION` (3.11), which always resolves the
  `>=83.0.0` branch above, so a future advisory affecting only the `<83` range would reach 3.9
  dev environments with the CVE gate green. `78.1.1` sits above the newest setuptools advisory.
  This costs nothing in practice — pip resolves 82.0.1 on 3.9 either way (verified with
  `pip install --dry-run -e ".[dev]"` in a real 3.9 venv) — so the functional floor is still
  satisfied with room to spare.
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
four legs run the same install + test commands as before, narrowed per #4 to
`pip install -e ".[test]"` + `pytest --cov-report=xml`.

**Rationale**:
- `fail-fast: false` is required by spec.md User Story 3 Acceptance Scenario 2: a failure
  specific to one version must be identifiable while the *other* versions still report their
  own independent pass/fail — the default `fail-fast: true` would cancel in-flight legs on
  the first failure, hiding whether the change would have passed on the others.
- A native GitHub Actions matrix (rather than routing CI through `tox`) keeps the `test` job
  structurally identical to every other job in this workflow (`lint`, `typecheck`, `security`,
  etc. — checkout, setup-python, the project install, run command) with only the
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

## #4: `tox.ini` command parity with CI, and the dependency set both install

**Decision**: `tox.ini`'s `[testenv]` runs a bare `pytest`, and CI's `test` job runs
`pytest --cov-report=xml`. Everything else — `--cov=mfgparams`, `--cov-report=term-missing`,
`--cov-fail-under=90` — comes from `[tool.pytest.ini_options].addopts`, which both inherit.
Both install `.[test]`, a narrow extra (`pytest`, `pytest-cov`, `pyyaml`, `build`) that `dev`
in turn depends on via `mfgparams[test]`.

**Rationale (invocation)**: The coverage threshold must have exactly one definition. Note that
pytest's *command-line* `--cov-fail-under` **overrides** `addopts` rather than merging with it,
so the first implementation — which restated the full flag list in CI's `run:` line "for
parity" — actually recreated the drift it was meant to prevent: raising the gate to 95 in
`pyproject.toml` would have raised it for `tox` while CI silently kept enforcing 90. Only the
one flag CI genuinely needs beyond the shared set (`--cov-report=xml`, consumed by the Codecov
upload step) is passed explicitly (code review finding).

**Rationale (dependency set)**: `extras = dev` would install the entire toolchain — `sphinx`,
`mypy`, `bandit`, `radon`, `black`, `pip-audit`, even `tox` itself — into all four
environments just to run `pytest`. Beyond the cost, that reintroduces the exact failure class
this feature exists to fix: the day any of those tools drops Python 3.9, `tox -e py39` and
CI's `test (3.9)` leg fail *at install time* even though mfgparams is perfectly fine on 3.9 —
identical in shape to the `setuptools>=83` pin that made `pip install -e ".[dev]"` unresolvable
on 3.9 in the first place (#2). A dedicated `test` extra decouples the version gate from
unrelated tooling; `dev` lists `mfgparams[test]` so the two cannot drift apart.

`build` is part of that extra deliberately, and the two tests that use it share a single
module-scoped wheel build rather than one each — `build`'s default isolated mode pip-installs
the `[build-system]` backend into a throwaway env, so halving the builds halves that cost
across all four matrix legs. Isolated mode is kept rather than `--no-isolation` because it is
the path a real `pip install mfgparams` takes, which is the property these tests exist to
assert; the environment running them already had to reach PyPI to install `.[test]`, so this
introduces no new class of dependency (code review finding).
`tests/integration/test_packaging_bundled_data.py` shells out to `python -m build` and asserts
the bundled `data/*.toml` files really ship inside the wheel, but guards itself with
`pytest.importorskip("build.__main__")`. With `build` installed nowhere that runs pytest, those
assertions were skipped in every tox env and every CI matrix leg, so dropping a path from
`[tool.setuptools.package-data]` would have shipped silently — the guard was hardened by this
feature but had nothing to guard (code review finding).

**Consequence for narrowed local runs**: because the 90% gate lives in `addopts`, it applies to
*any* pytest invocation, including a deliberately narrowed one — `tox -e py39 -- -k drilling`
reports the env FAILED on coverage even when every selected test passed, burying the real
failure being chased. `tox.ini` and README both document `--no-cov` alongside any filter
(code review finding). Note also that `--cov-report` *accumulates* addopts and command-line
values (pytest-cov's `StoreReport` action), while `--cov-fail-under` does not — only the latter
is a genuine override, which is why CI can safely add `--cov-report=xml` but must not restate
the threshold.

**Considered and declined — narrowing `dependency-scan`'s scope.** Adding `tox`, `build` and
`pyyaml` to `dev` also pulls their transitives (`virtualenv`, `filelock`, `platformdirs`,
`pyproject_hooks`, …) into the environment `dependency-scan` audits, so a CVE in purely-local
orchestration tooling can fail a required check even though nothing shipped depends on it. A
code review noted this sits in tension with pinning the `<3.10` `setuptools` floor high
*because* pip-audit coverage matters (#2). Declined for this feature, for two reasons: the
`dev` extra already carried eight dev-only tools (`sphinx`, `mypy`, `bandit`, `radon`, `black`,
`ruff`, `pip-audit`, `setuptools`) and their transitives before this change, so the increment
adds no new *class* of exposure; and narrowing the audit to runtime dependencies would rewrite
`003-ci-quality-security-gates`'s FR-005 contract and would trade a noisy gate for a blind one
— a dev-tool CVE is still worth knowing about. If the noise becomes a real problem, the right
fix is a scoped `pip-audit` policy in that feature, not a smaller `dev` extra here.

**Alternatives considered**: Duplicating the full flag list explicitly in `tox.ini` for
"clarity" — rejected, since it reintroduces exactly the drift risk this decision avoids. A bare
`deps = pytest, pytest-cov, pyyaml, build` list in `tox.ini` instead of an extra — rejected
because CI's `test` job needs the same set, and a `tox.ini`-only list would be a second place
to maintain it.

## #5: Keeping `quality-summary`'s single-value coverage output correct, and restricting the Codecov upload

**Decision** (reached after two `/code-review` corrections — the discarded attempts are recorded
below): the `test` job publishes **no** `coverage_pct` job output at all. Its canonical leg
(`if: always() && matrix.python-version == env.PYTHON_VERSION`) writes `coverage report
--format=total` to a `coverage-pct.txt` artifact, and `quality-summary` downloads that artifact
and reads the number into `TEST_METRIC`. The Codecov upload stays gated to the same canonical
leg.

**Attempt 1 (incorrect)**: gate *both* the Codecov upload and the `coverage_pct` job-output step
behind `if: matrix.python-version == '3.11'`, reasoning that pinning the output's source to one
leg keeps it deterministic. A GitHub Actions matrix job's `output` is published from whichever
leg's job instance *completes last*, not from whichever leg actually set a non-empty value —
so gating three of four legs out meant `needs.test.outputs.coverage_pct` resolved to an empty
string whenever one of those legs finished last, and `quality-summary`'s coverage cell
intermittently went missing with no job failing to flag it.

**Attempt 2 (also incorrect)**: remove the gate so *every* leg sets `coverage_pct`, on the
reasoning that coverage is a property of the code under test rather than of the interpreter, so
all four values would be identical and the race would be harmless. That premise is false in this
repository: `src/mfgparams/config.py` and `src/mfgparams/registry_config.py` each carry an
interpreter-conditional `tomllib` / `tomli` import fallback, so 3.9 and 3.10 execute two lines
that 3.11+ never reach. This feature's own validation run measured the difference directly —
98.88% on 3.9 versus 98.59% on 3.11/3.12. Every leg setting the same output name therefore still
publishes a *nondeterministic* number, just one that is never empty; rounding to a whole
percentage hides it today but does not fix it.

**Final rationale**: a matrix job simply cannot expose an attributable per-version value through
a job output — all legs write the same output name and last-writer-wins, so no arrangement of
`if:` gates is deterministic. An artifact has no such collision: only the canonical leg writes
it, so the number `quality-summary` renders is always that one named interpreter's, regardless of
leg finish order or of coverage genuinely differing between interpreters. `if: always()` on the
recording step keeps the metric available when the canonical leg's `pytest` step failed (the
partial result is exactly what a reviewer wants to see then), and `|| true` keeps `coverage
report`'s below-`fail_under` non-zero exit from failing the step on top of that. On the consuming
side, `continue-on-error: true` on the download means a `test` job that never produced the
artifact leaves the documented "—" placeholder rather than failing `quality-summary`.

The Codecov-upload gate's literal `'3.11'` was likewise changed to `env.PYTHON_VERSION` so it
cannot independently drift from the one declared canonical version, and
`tests/static/test_python_version_consistency.py` gained a check asserting `env.PYTHON_VERSION`
is always a member of the supported-version set — so dropping that version from the matrix
without updating `PYTHON_VERSION` (or vice versa) fails a test instead of silently leaving both
canonical-leg conditions permanently false.

**Alternatives considered**: Four uniquely named per-version job outputs (`coverage_pct_39`, …)
aggregated by `quality-summary` — rejected because it multiplies the workflow surface by four to
report one headline number, and each output still individually depends on matrix-output
semantics. Excluding the `tomllib`/`tomli` fallbacks from coverage measurement with `# pragma: no
cover` so all legs really do agree — rejected because it makes the reported number depend on an
invariant that any future interpreter-conditional line silently breaks, whereas the artifact is
correct whether or not the legs agree. A separate non-matrixed job that re-runs the suite purely
to produce the canonical number — rejected as a duplicate full test run.

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
- **Regex-scraping `ci.yml` for `python-version: [...]`** (as first implemented, replaced after
  a code-review finding): a regex matches the *first* such list anywhere in the file, so the
  guard was not actually scoped to the `test` job. Adding any other matrixed job above `test`
  would have silently pointed the check at the wrong matrix and let the `test` matrix drift
  unnoticed — defeating the very requirement it exists to enforce. Replaced by
  `yaml.safe_load` and an explicit `jobs["test"]["strategy"]["matrix"]["python-version"]`
  lookup (and the same for `env.PYTHON_VERSION`), with an assertion that each version is a
  quoted string, since unquoted YAML `3.10` parses as the float `3.1` and would compare
  unequal to the `"3.10"` classifier for a non-obvious reason. `pyyaml` is declared explicitly
  in the `test` extra for this rather than relied on as a transitive `bandit` dependency.
