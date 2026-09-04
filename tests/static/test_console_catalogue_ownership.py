"""Static check: every console string resolves from the console's own catalogue.

FR-001/SC-001 require this "enforced automatically, not by convention"
(mirroring 014's precedent, contracts/catalogue-ownership-contract.md). Five
checks here, each catching a regression class the others cannot see:

1. Every string-literal key `console/cli.py` passes to `translate()`/
   `has_message()` — directly, through a module-level lookup dict (e.g.
   `_MODE_OPTION_KEYS`), or through a chain of same-file function
   parameters (e.g. a `label_key`/`engagement_label_key` argument threaded
   through one or more wrapper functions before reaching the call) —
   exists in `mfgparams.console.locales.en.MESSAGES`.
2. `translate`/`has_message` are bound in `console/cli.py` **only** from
   `mfgparams.console.i18n` — never from `mfgparams.i18n` or anywhere
   else. Check 1 assumes a bare `translate`/`has_message` call means the
   console's catalogue; this is what makes that assumption true rather
   than merely convenient.
3. `console.missing_dependency*` is present in core's catalogue and absent
   from the console's — the sole FR-002 exception.
4. Every `message_key=` value that reaches an `ErrorInfo(...)` call
   anywhere core builds one (`validation.py`, milling's `_calculate.py`,
   drilling's `__init__.py`) — directly, or via the same kind of
   same-file parameter indirection as check 1 (e.g. `_reject_if_invalid`'s
   `error_message_key` keyword-only parameter) — resolves in core's
   catalogue (FR-005). Confirms research.md #4's move did not
   over-relocate something core still needs.
5. The two catalogues' key sets are disjoint, except
   `console.missing_dependency*` (core only) and the three dual-use label
   keys found during T007 implementation and documented in
   contracts/catalogue-ownership-contract.md (both, deliberately).

Checks 1 and 4 share the same underlying problem — a catalogue key does
not always appear as a literal argument at the call site that ultimately
consumes it — and so share one general solution below (`_propagate_and
_collect`): a small fixed-point analysis over same-file function calls,
rather than two hand-written special cases. An earlier version of this
file scanned only direct literal arguments, which a Copilot review found
missed exactly this: `_reject_if_invalid`'s `error_message_key` parameter
(check 4) and `_MODE_OPTION_KEYS`/`label_key`-style indirection in
`console/cli.py` (check 1), in both cases silently failing to guard the
key it claimed to guard.
"""

from __future__ import annotations

import ast
from pathlib import Path

import mfgparams
import mfgparams.console.locales.en as console_en
import mfgparams.locales.en as core_en

_SRC = Path(mfgparams.__file__).parent
_CLI_PATH = _SRC / "console" / "cli.py"

#: The one subtree that never constructs a *core* `ErrorInfo` — it only
#: displays one. Everything else under `src/mfgparams/` is in scope for
#: `test_core_still_has_every_key_its_own_error_messages_need`, discovered
#: by walking the tree rather than naming specific files: a hardcoded list
#: of "the modules that build ErrorInfo today" silently stops covering a
#: future process/operation module the day one is added (found by review —
#: an earlier version of this file named exactly three files).
_CONSOLE_SUBTREE = _SRC / "console"


def _non_console_source_files() -> list[Path]:
    return [path for path in sorted(_SRC.rglob("*.py")) if _CONSOLE_SUBTREE not in path.parents]


_CONSOLE_I18N_MODULE = "mfgparams.console.i18n"
_CONSOLE_TRANSLATE_FUNCS = {"translate", "has_message"}

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


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _literal_str(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


# --- Direct literal keys (no indirection) -----------------------------------


def _console_translate_calls(tree: ast.AST) -> list[ast.Call]:
    """Every call to a bare `translate`/`has_message` name within ``tree``."""

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _CONSOLE_TRANSLATE_FUNCS
    ]


def _direct_console_literal_keys(tree: ast.Module) -> set[str]:
    """Literal second arguments to a direct `translate(locale, "...")` call."""

    keys: set[str] = set()
    for call in _console_translate_calls(tree):
        if len(call.args) >= 2:
            lit = _literal_str(call.args[1])
            if lit is not None:
                keys.add(lit)
    return keys


def _module_level_dict_literal_string_values(tree: ast.Module) -> set[str]:
    """String literals used as values in a module-level dict literal.

    Catches lookup tables such as `_MODE_OPTION_KEYS = {mode: "cli...."}`
    whose values are catalogue keys consumed via `dict[...]` or `.items()`
    rather than as a direct call argument.
    """

    keys: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for value_node in node.value.values:
                lit = _literal_str(value_node)
                if lit is not None:
                    keys.add(lit)
    return keys


def _is_call_to(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name


def _direct_error_info_message_keys(tree: ast.Module) -> set[str]:
    """Literal `message_key=` values passed directly to an `ErrorInfo(...)` call."""

    keys: set[str] = set()
    for node in ast.walk(tree):
        if not _is_call_to(node, "ErrorInfo"):
            continue
        assert isinstance(node, ast.Call)
        for kw in node.keywords:
            if kw.arg != "message_key":
                continue
            lit = _literal_str(kw.value)
            if lit is not None:
                keys.add(lit)
    return keys


# --- Indirected keys: same-file parameter chains ----------------------------


def _function_defs(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def _param_names(fn: ast.FunctionDef) -> list[str]:
    return [a.arg for a in fn.args.args] + [a.arg for a in fn.args.kwonlyargs]


def _call_arg_for_param(call: ast.Call, fn: ast.FunctionDef, param: str) -> ast.expr | None:
    """The AST node bound to ``param`` in ``call`` — by keyword, else by position."""

    for kw in call.keywords:
        if kw.arg == param:
            return kw.value
    positional = [a.arg for a in fn.args.args]
    if param in positional:
        idx = positional.index(param)
        if idx < len(call.args):
            return call.args[idx]
    return None


def _default_for_param(fn: ast.FunctionDef, param: str) -> ast.expr | None:
    positional = [a.arg for a in fn.args.args]
    if param in positional:
        idx = positional.index(param)
        defaults = fn.args.defaults
        first_default_idx = len(positional) - len(defaults)
        if idx >= first_default_idx:
            return defaults[idx - first_default_idx]
        return None
    kwonly = [a.arg for a in fn.args.kwonlyargs]
    if param in kwonly:
        return fn.args.kw_defaults[kwonly.index(param)]
    return None


def _positional_sink_hit(
    node: ast.Call, params: set[str], positional_sinks: set[tuple[str, int]]
) -> str | None:
    """The local parameter name fed into a positional sink by ``node``, if any."""

    assert isinstance(node.func, ast.Name)
    for sink_callee, idx in positional_sinks:
        if node.func.id == sink_callee and len(node.args) > idx:
            arg = node.args[idx]
            if isinstance(arg, ast.Name) and arg.id in params:
                return arg.id
    return None


def _keyword_sink_hit(
    node: ast.Call, params: set[str], keyword_sinks: set[tuple[str, str]]
) -> str | None:
    """The local parameter name fed into a keyword sink by ``node``, if any."""

    assert isinstance(node.func, ast.Name)
    for sink_callee, kwname in keyword_sinks:
        if node.func.id != sink_callee:
            continue
        for kw in node.keywords:
            if kw.arg == kwname and isinstance(kw.value, ast.Name) and kw.value.id in params:
                return kw.value.id
    return None


def _seed_key_consuming_params(
    tree: ast.Module,
    positional_sinks: set[tuple[str, int]],
    keyword_sinks: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    """(function name, parameter name) pairs used directly as a sink's key argument.

    ``positional_sinks`` is a set of (callee name, positional index) — for
    external functions such as `translate`/`has_message`, where only the
    call convention (key is argument 1) is known, not a parameter name.
    ``keyword_sinks`` is a set of (callee name, keyword name) — for
    external functions such as `ErrorInfo`, whose key-bearing argument is
    always passed by keyword in this codebase.
    """

    functions = _function_defs(tree)
    result: set[tuple[str, str]] = set()
    for fn_name, fn in functions.items():
        params = set(_param_names(fn))
        for node in ast.walk(fn):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            hit = _positional_sink_hit(node, params, positional_sinks) or _keyword_sink_hit(
                node, params, keyword_sinks
            )
            if hit is not None:
                result.add((fn_name, hit))
    return result


def _propagated_via_one_call(
    node: ast.Call,
    caller_params: set[str],
    callee_fn: ast.FunctionDef,
    key_consuming: set[tuple[str, str]],
) -> str | None:
    """If ``node`` passes one of ``caller_params`` into an already
    key-consuming parameter of ``callee_fn``, return that caller parameter
    name — the caller inherits key-consuming status through this call."""

    assert isinstance(node.func, ast.Name)
    for param in _param_names(callee_fn):
        if (node.func.id, param) not in key_consuming:
            continue
        arg = _call_arg_for_param(node, callee_fn, param)
        if isinstance(arg, ast.Name) and arg.id in caller_params:
            return arg.id
    return None


def _propagate_to_fixed_point(
    tree: ast.Module, functions: dict[str, ast.FunctionDef], seed: set[tuple[str, str]]
) -> set[tuple[str, str]]:
    """Grow ``seed`` until no same-file call propagates key-consuming status
    to a new (function, parameter) pair.

    A parameter is key-consuming if it is passed — anywhere in this file —
    into another parameter already known to be key-consuming. Iterating to
    a fixed point (rather than one hop) handles a chain of any length, e.g.
    `engagement_label_key` threaded through two wrapper functions before it
    reaches `_prompt_validated_length`'s `label_key`, which is what
    actually calls `translate()`.
    """

    key_consuming = set(seed)
    changed = True
    while changed:
        changed = False
        for fn_name, fn in functions.items():
            params = set(_param_names(fn))
            for node in ast.walk(fn):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                    continue
                callee_fn = functions.get(node.func.id)
                if callee_fn is None:
                    continue
                hit = _propagated_via_one_call(node, params, callee_fn, key_consuming)
                if hit is not None and (fn_name, hit) not in key_consuming:
                    key_consuming.add((fn_name, hit))
                    changed = True
    return key_consuming


def _literals_bound_to(
    tree: ast.Module, functions: dict[str, ast.FunctionDef], key_consuming: set[tuple[str, str]]
) -> set[str]:
    """Every literal (default value, or an actual call-site argument) ever
    bound to a key-consuming (function, parameter) pair."""

    literals: set[str] = set()
    for fn_name, param in key_consuming:
        lit = _literal_str(_default_for_param(functions[fn_name], param))
        if lit is not None:
            literals.add(lit)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        callee_fn = functions.get(node.func.id)
        if callee_fn is None:
            continue
        for param in _param_names(callee_fn):
            if (node.func.id, param) not in key_consuming:
                continue
            lit = _literal_str(_call_arg_for_param(node, callee_fn, param))
            if lit is not None:
                literals.add(lit)
    return literals


def _propagate_and_collect(tree: ast.Module, seed: set[tuple[str, str]]) -> set[str]:
    """Fixed-point-propagate key-consuming (function, parameter) pairs through
    same-file calls, then collect every literal ever bound to one."""

    functions = _function_defs(tree)
    key_consuming = _propagate_to_fixed_point(tree, functions, seed)
    return _literals_bound_to(tree, functions, key_consuming)


def _all_console_keys(tree: ast.Module) -> set[str]:
    seed = _seed_key_consuming_params(
        tree,
        positional_sinks={("translate", 1), ("has_message", 1)},
        keyword_sinks=set(),
    )
    return (
        _direct_console_literal_keys(tree)
        | _module_level_dict_literal_string_values(tree)
        | _propagate_and_collect(tree, seed)
    )


def _all_error_info_message_keys(tree: ast.Module) -> set[str]:
    seed = _seed_key_consuming_params(
        tree,
        positional_sinks=set(),
        keyword_sinks={("ErrorInfo", "message_key")},
    )
    return _direct_error_info_message_keys(tree) | _propagate_and_collect(tree, seed)


# --- Tests -------------------------------------------------------------------


def test_console_keys_resolve_in_the_console_catalogue():
    """No exception for `_CORE_ONLY_EXCEPTION` here, deliberately: `console/cli.py`
    has no legitimate reason to ever call the console's own `translate()`/
    `has_message()` with `console.missing_dependency*` — that key exists to say
    the console is unavailable (it is used by `__main__.py`'s guard, via
    `_translate_core`, not by this module at all), so it is intentionally
    absent from the console's catalogue. Excluding it here would have let
    `console/cli.py` call it via the console-bound `translate()` — which
    would render the raw key — pass unnoticed.
    """

    tree = _parse(_CLI_PATH)
    keys = _all_console_keys(tree)

    assert keys, "expected to find at least one translate()/has_message() key"
    missing = {key for key in keys if key not in console_en.MESSAGES}
    assert not missing, f"console/cli.py uses keys absent from its own catalogue: {missing}"


def test_console_translate_bindings_come_only_from_console_i18n():
    """Check 1 assumes a bare `translate`/`has_message` call means the
    console's catalogue. Verify that assumption directly: both names must
    be imported from `mfgparams.console.i18n` and from nowhere else in
    this file — reverting `console/cli.py` to import from `mfgparams.i18n`
    would otherwise leave check 1 green while console keys render as raw
    IDs (a Copilot review finding on an earlier version of this file).
    """

    tree = _parse(_CLI_PATH)
    bindings: dict[str, set[str | None]] = {name: set() for name in _CONSOLE_TRANSLATE_FUNCS}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        for alias in node.names:
            name = alias.asname or alias.name
            if name in _CONSOLE_TRANSLATE_FUNCS:
                bindings[name].add(node.module)

    for name, modules in bindings.items():
        assert modules == {_CONSOLE_I18N_MODULE}, (
            f"{name!r} must be imported from {_CONSOLE_I18N_MODULE!r} only, " f"found: {modules}"
        )


def test_console_missing_dependency_is_the_sole_core_only_exception():
    assert _CORE_ONLY_EXCEPTION in core_en.MESSAGES
    assert f"{_CORE_ONLY_EXCEPTION}.unnamed" in core_en.MESSAGES
    assert _CORE_ONLY_EXCEPTION not in console_en.MESSAGES
    assert f"{_CORE_ONLY_EXCEPTION}.unnamed" not in console_en.MESSAGES


def test_core_still_has_every_key_its_own_error_messages_need():
    needed: set[str] = set()
    for path in _non_console_source_files():
        needed |= _all_error_info_message_keys(_parse(path))
    assert needed, "expected to find at least one message_key"
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
