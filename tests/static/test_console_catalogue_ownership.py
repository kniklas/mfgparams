"""Static check: every console string resolves from the console's own catalogue.

FR-001/SC-001 require this "enforced automatically, not by convention"
(mirroring 014's precedent, contracts/catalogue-ownership-contract.md). Five
checks here, each catching a regression class the others cannot see:

1. Every string-literal key `console/cli.py` passes to `translate()`/
   `has_message()` (the console's, imported from `mfgparams.console.i18n`)
   exists in `mfgparams.console.locales.en.MESSAGES`.
2. `console.missing_dependency*` is present in core's catalogue and absent
   from the console's — the sole FR-002 exception.
3. Every `message_key=` literal constructed anywhere core builds an
   `ErrorInfo` (`validation.py`, milling's `_calculate.py`, drilling's
   `__init__.py`) resolves in core's catalogue (FR-005) — confirms
   research.md #4's move did not over-relocate something core still needs.
4. The two catalogues' key sets are disjoint, except
   `console.missing_dependency*` (core only) and the three dual-use label
   keys found during T007 implementation and documented in
   contracts/catalogue-ownership-contract.md (both, deliberately).

Deliberately NOT checked here: that every call to the console's `translate`/
`has_message` uses a string literal. Several call sites legitimately thread
a key through a parameter (e.g. a `label_key` argument, always populated
with a console-owned literal by its own callers) — a per-call-site
literal-or-not scan cannot distinguish that from the two genuinely
core-owned dynamic keys (`RegistryConfigError.message_key`,
`materials_load_notice()`'s `notice_key`, both routed through the
separately imported `_translate_core`) without also flagging normal
indirection. Check 1 above still catches every *literal* key exhaustively;
a literal key hidden behind indirection would need a call-graph analysis
this file does not attempt.
"""

from __future__ import annotations

import ast
from pathlib import Path

import mfgparams
import mfgparams.console.locales.en as console_en
import mfgparams.locales.en as core_en

_SRC = Path(mfgparams.__file__).parent
_CLI_PATH = _SRC / "console" / "cli.py"
_VALIDATION_PATH = _SRC / "validation.py"
_MILLING_CALCULATE_PATH = _SRC / "processes" / "machining" / "milling" / "_calculate.py"
_DRILLING_INIT_PATH = _SRC / "processes" / "machining" / "drilling" / "__init__.py"

#: The sole FR-002 exception: a `console.*`-prefixed key that stays in core.
_CORE_ONLY_EXCEPTION = "console.missing_dependency"

#: Keys with a structural reason to exist in both catalogues (T007 finding;
#: see contracts/catalogue-ownership-contract.md). Not an oversight — do not
#: "fix" by removing either copy without updating that contract first.
_DUAL_PRESENCE_KEYS = {
    "cli.label.axial_depth_of_cut",
    "cli.label.radial_depth_of_cut",
    "cli.label.width_of_cut",
}

_CONSOLE_TRANSLATE_FUNCS = {"translate", "has_message"}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _console_translate_calls(tree: ast.Module) -> list[ast.Call]:
    """Every call to the console's own `translate`/`has_message` in ``tree``."""

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _CONSOLE_TRANSLATE_FUNCS
    ]


def _literal_key(call: ast.Call) -> str | None:
    """The key argument of a `translate(locale, key, ...)`-shaped call, if literal."""

    if len(call.args) < 2:
        return None
    key_arg = call.args[1]
    if isinstance(key_arg, ast.Constant) and isinstance(key_arg.value, str):
        return key_arg.value
    return None


def _error_info_message_keys(path: Path) -> set[str]:
    """Every literal `message_key=` value passed to an `ErrorInfo(...)` call."""

    tree = _parse(path)
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "ErrorInfo":
            continue
        for kw in node.keywords:
            if kw.arg == "message_key" and isinstance(kw.value, ast.Constant):
                keys.add(kw.value.value)
    return keys


def test_console_literal_keys_resolve_in_the_console_catalogue():
    tree = _parse(_CLI_PATH)
    calls = _console_translate_calls(tree)
    literal_keys = {key for call in calls if (key := _literal_key(call)) is not None}

    assert literal_keys, "expected to find at least one translate()/has_message() call"
    missing = {
        key
        for key in literal_keys
        if key not in console_en.MESSAGES and key != _CORE_ONLY_EXCEPTION
    }
    assert not missing, f"console/cli.py uses keys absent from its own catalogue: {missing}"


def test_console_missing_dependency_is_the_sole_core_only_exception():
    assert _CORE_ONLY_EXCEPTION in core_en.MESSAGES
    assert f"{_CORE_ONLY_EXCEPTION}.unnamed" in core_en.MESSAGES
    assert _CORE_ONLY_EXCEPTION not in console_en.MESSAGES
    assert f"{_CORE_ONLY_EXCEPTION}.unnamed" not in console_en.MESSAGES


def test_core_still_has_every_key_its_own_error_messages_need():
    needed = (
        _error_info_message_keys(_VALIDATION_PATH)
        | _error_info_message_keys(_MILLING_CALCULATE_PATH)
        | _error_info_message_keys(_DRILLING_INIT_PATH)
    )
    assert needed, "expected to find at least one message_key= literal"
    missing = needed - set(core_en.MESSAGES)
    assert not missing, f"core builds ErrorInfo with message_key(s) it cannot render: {missing}"


def test_no_key_exists_in_both_catalogues_except_the_documented_exceptions():
    shared = set(core_en.MESSAGES) & set(console_en.MESSAGES)
    unexpected = shared - _DUAL_PRESENCE_KEYS
    assert not unexpected, (
        f"key(s) present in both catalogues without a documented reason: {unexpected} "
        "— see contracts/catalogue-ownership-contract.md"
    )
    # And the documented exceptions really are present on both sides, not
    # just absent from `unexpected` because they are missing from one side.
    assert _DUAL_PRESENCE_KEYS <= shared
