# Quickstart: Validating Process Namespaces and Installation Extras

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Runnable checks that prove this feature works end to end. Run from the repository root. Each section
names the requirement it validates, so a failure points straight at what broke.

## Prerequisites

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

---

## 1. Nothing about the calculations changed (FR-003, FR-005, SC-001)

The primary regression evidence. The contract and integration suites moved with only import-line
edits, so a green run here means results are identical before and after.

```bash
pytest tests/contract tests/integration -q
```

**Expected**: all pass, zero skips beyond the pre-existing ones.

Spot-check the public surface directly — every name must import from the top level, unchanged:

```bash
python -c "
import mfgparams
for n in mfgparams.__all__:
    getattr(mfgparams, n)
print(f'{len(mfgparams.__all__)} public names OK')
"
```

---

## 2. Process-qualified paths resolve (FR-001, FR-002, SC-007)

```bash
python -c "
import mfgparams.processes.machining.drilling as d
import mfgparams.processes.machining.milling.end_milling as em
import mfgparams.processes.machining.milling.face_milling as fm
print('process paths OK')
"
```

**Expected**: no output but the success line. Note milling's retained sub-operation level — end and
face milling are *within* milling, not siblings of drilling.

---

## 3. Old paths are gone and cannot come back (FR-004, FR-017, SC-004)

```bash
python -c "
import importlib
try:
    importlib.import_module('mfgparams.operations')
except ModuleNotFoundError:
    print('old namespace correctly absent')
else:
    raise SystemExit('FAIL: mfgparams.operations still importable')
"
pytest tests/static/test_no_old_layout.py -q
```

**Expected**: both pass. The static test also fails if a future change reintroduces the old path in
any tracked file's *contents or its path* — including a re-added shim, whose contents alone would
contain nothing to match.

---

## 4. Core never imports the console (FR-008)

```bash
pytest tests/static/test_core_does_not_import_console.py -q

python -c "
import sys, mfgparams
import mfgparams.processes.machining.drilling
assert 'mfgparams.console' not in sys.modules, 'FAIL: core pulled in the console'
print('core is console-free')
"
```

**Expected**: both pass. The second check is what keeps `__main__.py`'s exemption honest — it fails
if that lazy import is ever hoisted to module scope.

---

## 5. Console works, all three invocation forms (FR-012)

```bash
mfgparams --help; echo "exit=$?"
python -m mfgparams --help; echo "exit=$?"
python -m mfgparams.console --help; echo "exit=$?"

# And an interactive run terminated at the first prompt (the console exits on EOF;
# there is no quit command):
printf '' | mfgparams; echo "exit=$?"
printf '' | python -m mfgparams; echo "exit=$?"
printf '' | python -m mfgparams.console; echo "exit=$?"
```

**Expected**: all three forms print the same help text with `prog: mfgparams` and `exit=0`, and all
three EOF runs terminate cleanly with the same exit status as each other.

The third form is the one worth actually running rather than assuming: it is the only one that
reaches `mfgparams.__main__:main` indirectly, and `runpy` imports the `mfgparams.console` package
*before* the guard exists — see contracts/console-entry-contract.md.

---

## 6. Missing console dependencies are reported, not thrown (FR-011, SC-003)

The `console` extra is empty on delivery, so this path cannot be reached by uninstalling anything.
Reach it by simulating the dependency import failure, which is exactly what the automated test does:

```bash
pytest -q -k "console_missing_dependency"
```

**Expected**: passes, asserting a single actionable message on stderr naming
the install command — `<the running interpreter> -m pip install "mfgparams[console]"`, quoted
because unquoted zsh globs it and aborts before pip runs, and interpreter-qualified because a bare
`pip` can install into a different Python — a non-zero exit status, and **no traceback**.

---

## 7. A default install carries no console dependencies (FR-009, FR-013, SC-002)

```bash
python -m venv /tmp/mfgparams-core && /tmp/mfgparams-core/bin/pip install -q .
/tmp/mfgparams-core/bin/python -c "
from mfgparams import calculate, list_materials
print('core-only install: calculation API OK')
"
/tmp/mfgparams-core/bin/pip list --format=freeze
```

**Expected**: the calculation API works, and the installed list contains only `mfgparams` and, on
Python < 3.11, `tomli`.

---

## 8. Bundled data ships at the new paths (FR-015, SC-005)

```bash
tox -e packaging
```

**Expected**: passes. Asserts against a **built wheel** that all four `.toml` files are present at
their new paths and that no `.toml` remains under any `mfgparams/operations/` path. A source-tree
check would pass even with broken packaging metadata, which is the whole point of building first.

---

## 9. Full gates (SC-006)

```bash
tox                # py39-py312, excluding packaging assertions
ruff check src/ tests/ scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py
black --check src/ tests/ scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py
mypy src/mfgparams scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py
python scripts/check_maintainability.py src/ scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py
bandit -r src scripts/sync_agent_integrations.py scripts/setup_skill_symlinks.py -ll
pip-audit
python scripts/setup_skill_symlinks.py --check
```

**Expected**: all pass; coverage at or above 90%.

These are copied verbatim from `.github/workflows/ci.yml` so a local run and CI
measure the same thing. The earlier `ruff check . && black --check . && mypy` did not:
it scanned a wider tree than CI does and left `pip-audit`, the maintainability gate and
the skill-symlink check out entirely (corrected during T040).

`tox` reports `py311: SKIP` on a machine whose `python3.11` is not on `PATH`
(`skip_missing_interpreters = true`). CI runs that leg, so a local skip is not a gap --
but it does mean a local `tox` alone is not proof of the full matrix.

---

## 10. Docs reflect the new layout (FR-016)

```bash
sphinx-build -W -b html docs/source docs/_build/html
grep -rn "mfgparams\.operations" docs/ README.md || echo "no stale layout references"
```

**Expected**: docs build with warnings-as-errors, and the grep finds nothing.
