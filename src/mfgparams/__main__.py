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

import re
import sys

#: Message ID for the FR-011 guard. Its English text lives in the **core**
#: catalog and must stay there when slice 015 relocates the other catalogs
#: into the console: a message whose whole purpose is to say the console is
#: unavailable cannot be looked up from inside the console
#: (contracts/console-entry-contract.md).
_MISSING_CONSOLE_MESSAGE_ID = "console.missing_dependency"


def _is_broken_core(module: str | None) -> bool:
    """Is a failure to import ``module`` a broken install rather than a missing extra?

    Two kinds of failure reach the guard below, and telling the user the wrong
    one wastes their time on a fix that cannot work:

    * a module inside our own distribution -- the install is damaged;
    * a **core runtime requirement**, i.e. something a default
      ``pip install mfgparams`` was supposed to bring in (``tomli`` below
      Python 3.11). Its absence is equally a damaged install, and it is *not*
      a third-party name, so a check that only looked for the ``mfgparams``
      prefix would misreport it as a missing console extra and send the user
      to install something they already have.

    Anything else is a genuine console dependency, so the friendly path applies.
    """
    if not module:
        return False

    root = module.split(".")[0]
    if root == "mfgparams":
        return True

    return _normalise(root) in _core_requirement_roots()


def _normalise(name: str) -> str:
    return name.replace("-", "_").lower()


def _core_requirement_roots() -> frozenset:
    """Distribution names a default (no-extras) install pulls in.

    Read from installed metadata rather than restated here, so the set cannot
    drift from ``pyproject.toml``. Requirements carrying an ``extra ==`` marker
    are excluded: those are exactly the ones the guard's friendly path is for.
    """
    try:
        from importlib.metadata import requires

        declared = requires("mfgparams") or []
    except Exception:  # pragma: no cover - metadata missing (a source-tree run)
        return frozenset()

    roots = set()
    for requirement in declared:
        head, _, marker = requirement.partition(";")
        if "extra ==" in marker:
            continue
        name = re.split(r"[^A-Za-z0-9._-]", head.strip(), maxsplit=1)[0]
        if name:
            roots.add(_normalise(name))
    return frozenset(roots)


def main() -> int:
    """Start the interactive console, or explain how to install it (FR-011).

    Returns the process exit status: whatever the console returns once it has
    run to completion (``0`` when it returns nothing), or ``1`` if the console's
    dependencies are unavailable.
    """

    try:
        from mfgparams.console.cli import main as _console_main
    except ModuleNotFoundError as exc:
        # A damaged install must surface its own error rather than being
        # misreported as a missing extra -- the user cannot fix a missing core
        # dependency by installing `mfgparams[console]`.
        if _is_broken_core(exc.name):
            raise

        from mfgparams.i18n import get_locale, translate

        message = translate(
            get_locale(), _MISSING_CONSOLE_MESSAGE_ID, module=repr(exc.name or "a dependency")
        )
        print(message, file=sys.stderr)
        return 1

    # Pass the console's exit status through rather than assuming success. The
    # console returns None today, but swallowing a future non-zero return is a
    # silent failure, and this function documents itself as returning the
    # process exit status.
    status = _console_main()
    return 0 if status is None else int(status)


if __name__ == "__main__":
    raise SystemExit(main())
