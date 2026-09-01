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

import os
import re
import sys
from pathlib import Path

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


#: The extra a requirement is gated by, as written in the ``;`` marker. Quotes
#: may be single or double and the spacing around ``==`` is not guaranteed, so
#: the name is *parsed* rather than matched as a fixed substring: a marker this
#: failed to recognise would put an extra's dependency into the core set, where
#: :func:`_is_broken_core` calls it a damaged install and re-raises the very
#: traceback FR-011 exists to prevent.
_EXTRA_MARKER = re.compile(r"""extra\s*==\s*['"]([^'"]+)['"]""")


def _declared_requirements() -> list[tuple[str, str | None]]:
    """``(root_name, gating_extra)`` for every requirement in installed metadata.

    ``gating_extra`` is ``None`` for a requirement a default install pulls in.
    Read from metadata rather than restated here, so no set derived from it can
    drift from ``pyproject.toml``.
    """
    try:
        from importlib.metadata import requires

        declared = requires("mfgparams") or []
    except Exception:  # pragma: no cover - metadata missing (a source-tree run)
        return []

    parsed = []
    for requirement in declared:
        head, _, marker = requirement.partition(";")
        name = re.split(r"[^A-Za-z0-9._-]", head.strip(), maxsplit=1)[0]
        if name:
            found = _EXTRA_MARKER.search(marker)
            parsed.append((_normalise(name), found.group(1) if found else None))
    return parsed


def _core_requirement_roots() -> frozenset:
    """Distribution names a default (no-extras) install pulls in.

    Requirements gated by an extra are excluded: those are exactly the ones the
    guard's friendly path is for.
    """
    return frozenset(root for root, extra in _declared_requirements() if extra is None)


#: The console package, as an absolute path. Used to attribute a run-time
#: import failure to whoever asked for the module -- see
#: :func:`_requested_by_the_console`.
_CONSOLE_DIR = Path(__file__).parent / "console"


def _requesting_file(exc: BaseException) -> str | None:
    """The file whose code asked for the import that raised ``exc``.

    That is the deepest traceback frame belonging to *someone's code* rather
    than to the import machinery, which contributes frames of its own
    (``<frozen importlib._bootstrap>``, and ``importlib/__init__.py`` when a
    module is loaded through :func:`importlib.import_module`).
    """
    filenames = []
    traceback = exc.__traceback__
    while traceback is not None:
        filenames.append(traceback.tb_frame.f_code.co_filename)
        traceback = traceback.tb_next

    for filename in reversed(filenames):
        if filename.startswith("<") or os.path.basename(os.path.dirname(filename)) == "importlib":
            continue
        return filename
    return None


def _requested_by_the_console(exc: BaseException) -> bool:
    """Did code inside ``mfgparams.console`` ask for the module that is missing?

    Attribution by *name* cannot work here, which is the whole reason this
    function is about provenance instead. The gating extra records a
    **distribution** name (``PyYAML``) while the exception carries an **import**
    name (``yaml``), and the two differ for a large class of packages --
    ``Pillow``/``PIL``, ``beautifulsoup4``/``bs4``, ``python-dateutil``/
    ``dateutil``. Mapping between them needs the distribution's own metadata,
    which is precisely what is *not* installed at the moment the import fails.
    A name comparison would therefore miss every such package, and because this
    guard's default is to re-raise, every miss fails in the direction FR-011
    forbids.

    Provenance sidesteps the mapping entirely: whatever it is called, a module
    the console itself imported is the console's dependency, and
    ``pip install mfgparams[console]`` is the fix. A failure raised from inside
    a third-party library the console merely *called* is that library's bug and
    still re-raises, which is the property the name check was reaching for.
    """
    requester = _requesting_file(exc)
    if requester is None:
        return False

    # `Path.is_relative_to` is 3.9+, which is this project's floor.
    return Path(requester).resolve().is_relative_to(_CONSOLE_DIR.resolve())


def _report_missing_console(module: str | None) -> int:
    """Print the FR-011 message for ``module`` and return the exit status."""
    from mfgparams.i18n import get_locale, translate

    message = translate(
        get_locale(), _MISSING_CONSOLE_MESSAGE_ID, module=repr(module or "a dependency")
    )
    print(message, file=sys.stderr)
    return 1


def main() -> int:
    """Start the interactive console, or explain how to install it (FR-011).

    Returns the process exit status: whatever the console returns once it has
    run to completion (``0`` when it returns nothing), or ``1`` if the console's
    dependencies are unavailable.

    Both the import *and* the run are guarded. #63 explicitly permits the
    console to import a heavy dependency lazily, inside the call rather than at
    module scope -- and such an import fails after this function has already
    committed to running, where an unguarded call would emit exactly the raw
    traceback FR-011 forbids. The two guards ask different questions, because
    what identifies a console dependency differs once the console is running;
    see :func:`_requested_by_the_console`.
    """

    try:
        from mfgparams.console.cli import main as _console_main
    except ModuleNotFoundError as exc:
        # A damaged install must surface its own error rather than being
        # misreported as a missing extra -- the user cannot fix a missing core
        # dependency by installing `mfgparams[console]`.
        if _is_broken_core(exc.name):
            raise
        return _report_missing_console(exc.name)

    try:
        # Pass the console's exit status through rather than assuming success.
        # The console returns None today, but swallowing a future non-zero
        # return is a silent failure, and this function documents itself as
        # returning the process exit status.
        status = _console_main()
    except ModuleNotFoundError as exc:
        if not _requested_by_the_console(exc):
            raise
        return _report_missing_console(exc.name)

    return 0 if status is None else int(status)


if __name__ == "__main__":
    raise SystemExit(main())
