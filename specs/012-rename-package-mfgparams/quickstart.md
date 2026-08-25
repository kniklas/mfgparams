# Quickstart: Validating the mfgparams Rename

Run these checks after implementing the rename (post-`git mv` + substitution), before opening
the pull request. They exercise the guarantees in
[`contracts/package-identity-contract.md`](./contracts/package-identity-contract.md).

## Prerequisites

- A clean Python virtual environment (>=3.9) with the repo checked out on the
  `012-rename-package-mfgparams` branch.
- No pre-existing `machine_calc`/`mfgparams` installs in the environment (avoids false
  positives from a stale prior install).

## 1. Fresh install under the new name

```bash
python -m venv .venv-rename-check && source .venv-rename-check/bin/activate
pip install -e ".[dev]"
python -c "import mfgparams; print(mfgparams.__version__)"
```

**Expected**: install succeeds; the version string prints with no import error. (Validates
contract G2, G4.)

## 2. CLI entry point

```bash
mfgparams --help
```

**Expected**: usage/help text is shown under the `mfgparams` program name (not `machine-calc`),
listing the same options as before the rename. Then run one full interactive/CLI flow you'd
normally use (e.g. a drilling calculation) and confirm the prompts and result match what
`machine-calc` produced pre-rename. (Validates contract G3.)

## 3. No stray references

```bash
python -m pytest tests/static/test_no_old_package_name.py -v
```

**Expected**: passes — zero occurrences of `machine_calc`/`machine-calc` outside the documented
exclusions (repo-slug URLs, historical spec/CHANGELOG entries, gitignored build output).
(Validates contract G1; see `data-model.md`'s Exclusion rule for exactly what's allowed to
remain.)

## 4. Full test suite

```bash
python -m pytest
```

**Expected**: 100% of the pre-existing suite passes, at the same or higher coverage percentage
as before the rename (`--cov` now targets `mfgparams`, per `pyproject.toml`).

## 5. Package build

```bash
python -m build
ls dist/
```

**Expected**: build succeeds; every artifact in `dist/` is named `mfgparams-*` (e.g.
`mfgparams-<version>-py3-none-any.whl`), none named `machine_calc-*`/`machine-calc-*`.

## 6. Documentation build

```bash
sphinx-build -b html docs/source docs/_build/html
```

**Expected**: builds with no autodoc import errors (confirms every `automodule`/`autoclass`
directive in `docs/source/*.rst` now points at `mfgparams.*`).

## 7. Manual spot-check of intentionally-excluded references

```bash
grep -n "kniklas/machine-calc" README.md LICENSE.md
```

**Expected**: these lines are still present, unchanged — they are repository URLs, not package
identifiers, and are explicitly out of scope for this feature (see spec Clarifications and
`data-model.md`'s Exclusion rule). Their continued presence here is correct, not a regression.

## Cleanup

```bash
deactivate
rm -rf .venv-rename-check
```
