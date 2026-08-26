# Quickstart: Validating Verified Multi-Python-Version Local & CI Testing

**Prerequisites**: A local clone of `mfgparams`; for the full local multi-version check,
`pyenv` (or equivalent) with Python 3.9, 3.10, 3.11, and 3.12 installed so their `pythonX.Y`
commands are on `PATH`.

## 1. Confirm the Python 3.9 install path actually works (User Story 1)

```bash
~/.pyenv/versions/3.9.0/bin/python3 -m venv /tmp/py39-check
/tmp/py39-check/bin/python -m pip install --upgrade pip
/tmp/py39-check/bin/pip install -e ".[dev]"
/tmp/py39-check/bin/pytest --cov=mfgparams --cov-report=term-missing --cov-fail-under=90
```

**Expected outcome**: Both `pip install` steps succeed with no dependency-resolution error
(previously: `ERROR: Could not find a version that satisfies the requirement
setuptools>=83.0.0`), and the full suite passes with coverage ≥90%, matching the README's
documented steps exactly.

## 2. Check every supported version locally with one command (User Story 2)

```bash
pip install -e ".[dev]"   # now also installs tox
tox
```

**Expected outcome**: `tox` runs the suite once per available interpreter among
`py39`/`py310`/`py311`/`py312` and prints a per-version summary; any interpreter missing from
`PATH` shows as `SKIPPED`, not `FAILED`, and does not by itself fail the overall `tox` exit
code.

```bash
tox -e py39   # single-version inner loop
```

**Expected outcome**: Same suite, same coverage gate, restricted to one version — useful once
a specific version's failure has been identified from the full `tox` run above.

## 3. Confirm CI enforces every version independently (User Story 3)

1. Open a pull request that changes any file under `src/` or `tests/`.
2. **Expected**: the checks list shows four distinct entries — `test (3.9)`, `test (3.10)`,
   `test (3.11)`, `test (3.12)` — each independently pass/fail, not one combined `test` check.
3. On a scratch branch, introduce a change that only breaks on one specific version (e.g.,
   guard a code path with `if sys.version_info < (3, 10): raise RuntimeError("broken")`).
   Open a pull request.
4. **Expected**: only that version's check fails and is clearly labeled with its version; the
   other three still run to completion and report their own independent pass/fail (this
   requires `fail-fast: false` — contract: `contracts/multi-version-testing-contract.md`).
5. Revert the change; confirm all four checks turn green and the PR becomes mergeable again,
   subject to the repository's required-status-check list actually naming all four (see the
   "Required-status-check update" section of the contract — a one-time manual step, not
   re-validated by this scenario).
