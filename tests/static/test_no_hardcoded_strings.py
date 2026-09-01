"""Static check: no literal user-facing strings outside the message catalog
(T043a; Constitution VIII).

Parses ``cli.py`` and confirms every ``input(...)``/``print(...)`` call
site passes either no argument, a variable, or a call to
``mfgparams.i18n.translate(...)`` — never a hard-coded string literal —
so future edits cannot silently reintroduce untranslated text. Also
confirms ``logging_setup.py`` (the one place Constitution VIII requires
plain English) uses ordinary string literals, not catalog lookups.
"""

from __future__ import annotations

import ast
import inspect

from mfgparams import __main__ as entry_point
from mfgparams import logging_setup
from mfgparams.console import cli


def _call_sites(source: str, func_names: set[str]) -> list[ast.Call]:
    tree = ast.parse(source)
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in func_names
    ]


def test_cli_has_no_hardcoded_user_facing_strings():
    source = inspect.getsource(cli)
    calls = _call_sites(source, {"input", "print"})

    assert calls, "expected at least one input()/print() call site in cli.py"

    for call in calls:
        for arg in call.args:
            assert not isinstance(arg, ast.Constant) or not isinstance(arg.value, str), (
                "cli.py must source user-facing text from the message catalog "
                f"(translate()), found a literal string argument at line {call.lineno}"
            )


def test_the_entry_point_has_no_hardcoded_user_facing_strings():
    """`__main__.py` prints too, and Principle VIII does not stop at `cli.py`.

    The FR-011 message and the console's own error status both reach the user
    from here, so a literal added to either `print()` is untranslated output in
    the same sense `cli.py` is scanned for.

    This scan reads *direct* arguments only, which is the shape it can judge
    without guessing: `__main__.py` legitimately holds string literals that are
    not user-facing (message IDs, a marker regex). A literal buried inside a
    nested call is invisible to it -- that hole is covered at runtime by
    `test_the_unnamed_fallback_is_looked_up_rather_than_inlined`, which asserts
    editing the catalog changes the output.
    """

    source = inspect.getsource(entry_point)
    calls = _call_sites(source, {"input", "print"})

    assert calls, "expected at least one print() call site in __main__.py"

    for call in calls:
        for arg in call.args:
            assert not isinstance(arg, ast.Constant) or not isinstance(arg.value, str), (
                "__main__.py must source user-facing text from the message catalog "
                f"(translate()), found a literal string argument at line {call.lineno}"
            )


def test_logging_setup_uses_plain_english_not_the_catalog():
    source = inspect.getsource(logging_setup)
    assert "translate(" not in source
    assert "mfgparams.i18n" not in source and "from mfgparams.i18n" not in source


#: The milling session functions added by specs/009-milling-calculations.
#: The scan above walks the whole ``cli.py`` module, so these are already
#: covered — this list exists to fail loudly if the milling prompts are ever
#: moved into a module the scan does not read (009 T048).
_MILLING_CLI_FUNCTIONS = {
    "_prompt_operation",
    "_prompt_milling_sub_operation",
    "_prompt_mill_tool_choice",
    "_prompt_validated_length",
    "_prompt_milling_geometry",
    "_prompt_milling_inputs",
    "_run_end_milling_session",
    "_run_face_milling_session",
    "_run_milling_session",
}


def test_milling_session_functions_are_inside_the_scanned_surface():
    tree = ast.parse(inspect.getsource(cli))
    defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

    missing = _MILLING_CLI_FUNCTIONS - defined
    assert not missing, (
        "these milling CLI functions are no longer in cli.py, so the "
        f"hard-coded-string scan no longer covers them: {sorted(missing)}"
    )


def test_milling_prompts_are_translated():
    """Every milling prompt/print argument must be a translate() call."""

    tree = ast.parse(inspect.getsource(cli))
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in _MILLING_CLI_FUNCTIONS
    ]
    assert len(functions) == len(_MILLING_CLI_FUNCTIONS)

    checked = 0
    for function in functions:
        for call in _call_sites(ast.unparse(function), {"input", "print"}):
            for arg in call.args:
                assert not isinstance(arg, ast.Constant) or not isinstance(arg.value, str)
                checked += 1

    assert checked, "expected the milling session functions to emit some output"
