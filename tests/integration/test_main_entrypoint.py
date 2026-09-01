"""Smoke test for `python -m mfgparams` entry point (T025)."""

import subprocess
import sys

import pytest


def test_module_entrypoint_runs_and_exits_cleanly():
    proc = subprocess.run(
        [sys.executable, "-m", "mfgparams"],
        input="drilling\nmetric\nstandard\nMetal\nMild Steel\nCarbide\n10\n25\n\nn\n",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    assert "RPM" in proc.stdout


# --- `python -m mfgparams.console`, the direct console form ---------------
#
# Added by local review (L1). This module shim was manually exercised during
# T040 but had no test, leaving it the only 0%-covered file in the package.
#
# It originally called `console.cli.main` directly, deliberately bypassing the
# package-root guard. Copilot review banded that HIGH: FR-011 is unqualified,
# so the one invocation form a user reaches by guessing must not be the one
# that answers a missing dependency with a traceback. It now delegates to the
# guarded `mfgparams.__main__:main`, which is what the tests below exercise --
# that this form reaches a working console and reports an honest exit status,
# by the same route as the other two.


def _run_module(module: str, *args: str, stdin: str = "") -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_console_module_form_starts_and_exits_cleanly_on_eof():
    """`python -m mfgparams.console` reaches the REPL and leaves it cleanly."""

    result = _run_module("mfgparams.console", stdin="")

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr


def test_console_module_form_matches_the_package_root_help():
    """It is the same console, so it must produce the same `--help`."""

    direct = _run_module("mfgparams.console", "--help")
    via_package = _run_module("mfgparams", "--help")

    assert direct.returncode == 0, direct.stderr
    assert direct.stdout == via_package.stdout


def test_package_module_form_propagates_the_exit_status(monkeypatch):
    """`python -m mfgparams` must pass the console's status to the interpreter.

    The in-process twin of the subprocess checks above, and the only thing that
    measures `mfgparams/__main__.py`'s own `raise SystemExit(main())`. That line
    *is* the fix for "the console's exit status was discarded" -- a shim calling
    `main()` bare exits 0 no matter what the console reported. Its sibling
    `mfgparams/console/__main__.py` already has this test; the top-level entry
    point, which is the one users actually reach, did not.
    """

    import runpy

    import mfgparams.console.cli as console_cli

    monkeypatch.setattr(console_cli, "main", lambda: 5)
    # Other tests import this module by name; leaving it in sys.modules makes
    # runpy warn that it is re-executing an already-imported module. Dropping it
    # is what makes the re-execution the clean one the warning asks for.
    monkeypatch.delitem(sys.modules, "mfgparams.__main__", raising=False)

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("mfgparams", run_name="__main__")

    assert excinfo.value.code == 5


def test_console_module_form_propagates_the_exit_status(monkeypatch):
    """Executed in-process, so this measures the shim's own lines rather than a
    child interpreter's -- the subprocess tests above prove it works end to end
    but are invisible to coverage.

    A `python -m` shim that calls `main()` without `raise SystemExit(...)`
    always exits 0, discarding whatever the console reported. That failure is
    silent by construction, which is why it is asserted rather than assumed.
    """

    import runpy

    import mfgparams.console.cli as console_cli

    monkeypatch.setattr(console_cli, "main", lambda: 7)

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("mfgparams.console", run_name="__main__")

    assert excinfo.value.code == 7
