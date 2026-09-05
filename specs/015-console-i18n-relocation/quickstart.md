# Quickstart: Validating Console-Owned Message Catalogues

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

These are runnable checks that this feature works end-to-end, once implemented. They validate the
[error-info-contract](./contracts/error-info-contract.md) and the
[catalogue-ownership-contract](./contracts/catalogue-ownership-contract.md); see those for the full
rules being checked.

## Prerequisites

```bash
cd /path/to/mfgparams
python -m venv .venv && source .venv/bin/activate
pip install -e ".[console,dev]"
```

## 1. Library API stays usable without the console extra

```bash
pip uninstall -y mfgparams && pip install -e "." --no-deps  # core only, no [console]
python -c "
from mfgparams import calculate_end_milling
result = calculate_end_milling(0.0, 2.0, 5.0, 0.05, 4, 100.0, 'Mild Steel', 'Carbide')
assert result.error is not None
assert result.error.message and 'diameter' in result.error.message.lower()
assert result.error.message_key == 'error.invalid_mill_diameter.zero'
assert result.error.kwargs == ()
print('OK:', result.error.code, result.error.message)
"
```

**Expected**: prints an English error message and exits 0 — no `ModuleNotFoundError`, no import of
anything under `mfgparams.console`.

## 2. `MFGPARAMS_LOCALE` no longer changes `ErrorInfo.message`

```bash
pip install -e ".[console,dev]"  # restore full install for the rest of this guide
MFGPARAMS_LOCALE=zz-nonexistent python -c "
from mfgparams import calculate_end_milling
result = calculate_end_milling(0.0, 2.0, 5.0, 0.05, 4, 100.0, 'Mild Steel', 'Carbide')
print(result.error.message)
"
```

**Expected**: identical English text to check 1, regardless of `MFGPARAMS_LOCALE` — confirms FR-005/
FR-007 (this is the behaviour change `test_library_api_milling_locale.py` is rewritten to assert).

## 3. A shared `code` re-renders distinctly by `message_key`

```bash
python -c "
from mfgparams import calculate_end_milling

zero = calculate_end_milling(0.0, 2.0, 5.0, 0.05, 4, 100.0, 'Mild Steel', 'Carbide')
too_big = calculate_end_milling(1e6, 2.0, 5.0, 0.05, 4, 100.0, 'Mild Steel', 'Carbide')

assert zero.error.code == too_big.error.code  # both INVALID_DIAMETER
assert zero.error.message_key != too_big.error.message_key
assert too_big.error.kwargs  # carries max_mill_diameter_mm
print('codes match, message_keys differ:', zero.error.message_key, too_big.error.message_key)
"
```

**Expected**: confirms SC-006 — a `code` shared by two templates does not collapse them into one
`message_key`.

## 4. Every console string resolves from the console's own catalogue

```bash
pytest tests/static/test_console_catalogue_ownership.py -v
```

**Expected**: passes, and fails if a `cli.*`/`material_type.*` key is re-added to
`mfgparams/locales/en.py`, or if `console.missing_dependency*` is ever moved out of it (SC-001,
SC-004).

## 5. Full regression pass

```bash
pytest --cov=mfgparams --cov-report=term-missing
mypy src/mfgparams
ruff check src/mfgparams tests
```

**Expected**: full suite green, coverage at or above the project's existing threshold (SC-003), no
new type or lint errors — the standard bar every feature in this repository must clear
(Constitution Principles I, II, IX).

## What "done" looks like

- Checks 1-3 pass on a clean environment.
- Check 4 passes and demonstrably fails if the ownership rule is violated (verify once by
  temporarily re-adding a `cli.*` key to core's catalogue and confirming the test catches it, then
  revert).
- Check 5 passes with no regression against the baseline established before this feature.
