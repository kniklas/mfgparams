"""Entry points for ``mfgparams`` (console script) and ``python -m mfgparams``.

This module is the **single exemption** to the rule that the calculation core
never imports the console (FR-008): ``python -m mfgparams`` requires a
``__main__.py`` at the package root and the interpreter accepts no other
location. The exemption is narrowed by keeping the import inside
:func:`main`, so importing the ``mfgparams`` package itself still never pulls
in the console. Both halves are enforced by
``tests/static/test_core_does_not_import_console.py``, not by convention.
"""

from __future__ import annotations

import sys

#: Message ID for the FR-011 guard. Its English text lives in the **core**
#: catalog and must stay there when slice 015 relocates the other catalogs
#: into the console: a message whose whole purpose is to say the console is
#: unavailable cannot be looked up from inside the console
#: (contracts/console-entry-contract.md).
_MISSING_CONSOLE_MESSAGE_ID = "console.missing_dependency"


def main() -> int:
    """Start the interactive console, or explain how to install it (FR-011).

    Returns the process exit status: ``0`` once the console has run to
    completion, ``1`` if the console's dependencies are unavailable.
    """

    try:
        from mfgparams.console.cli import main as _console_main
    except ModuleNotFoundError as exc:
        # A module inside our own distribution failing to import is a broken
        # install, not a missing extra. Re-raise it rather than sending the
        # user to fix something that is not wrong.
        if exc.name is not None and exc.name.split(".")[0] == "mfgparams":
            raise

        from mfgparams.i18n import get_locale, translate

        print(translate(get_locale(), _MISSING_CONSOLE_MESSAGE_ID), file=sys.stderr)
        return 1

    _console_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
