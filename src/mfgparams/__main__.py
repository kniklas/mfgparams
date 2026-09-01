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

import importlib
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

    The console extra wins a tie. A requirement can be declared *both* without
    an extra and under ``console`` -- a core dependency carrying an environment
    marker that does not apply to the running interpreter, say, re-declared for
    the console. Ranking core first there would re-raise for a module
    ``pip install mfgparams[console]`` would genuinely have supplied, which is
    the one case where the friendly message is not just kind but correct. The
    question this function really answers is *"is this something the console
    extra cannot fix?"*, and that ordering is what keeps the answer honest.

    Both lookups compare an **import** name against **distribution** names, and
    those differ for a large class of packages (``PyYAML``/``yaml``). What that
    costs depends on which caller is asking, so the two are worth separating:

    * At **import time** it is free. The two lookups miss *together* -- a name
      matching neither set falls through to the friendly path, which is already
      the right answer there.
    * At **execution time** it is a real, bounded gap. That caller's default is
      to re-raise, so this function returning ``False`` is what *permits* the
      friendly message; a core requirement whose import name differs from its
      distribution name (a core ``PyYAML``, imported lazily by the console and
      missing) would be answered with ``pip install mfgparams[console]``, which
      cannot fix it.

    The gap is not closable from here: resolving a distribution name to the
    import name it provides needs that distribution's own metadata, which is by
    definition absent at the moment its import fails. What bounds it instead is
    how few core requirements there are -- ``tomli`` today, whose two names
    match. A core requirement whose names diverge is the case to think twice
    about, and this paragraph is the warning that it is not covered.
    """
    if not module:
        return False

    root = module.split(".")[0]
    if root == "mfgparams":
        return True

    if _normalise(root) in _console_extra_roots():
        return False

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


def _console_extra_roots() -> frozenset:
    """Distribution names the ``console`` extra would install.

    Empty on delivery, because the extra is (``pyproject.toml`` explains why).
    Read from metadata rather than restated, so it starts covering a dependency
    the day one is added with no second place to remember to update.

    Used only by :func:`_is_broken_core`, to decide whether the extra could
    supply a name that is *also* declared as a core requirement. It is
    deliberately **not** how a run-time failure is attributed to the console --
    see :func:`_requested_by_the_console` for why matching a distribution name
    against an import name cannot work there.
    """
    return frozenset(root for root, extra in _declared_requirements() if extra == "console")


#: The console package, as an absolute path. Used to attribute a run-time
#: import failure to whoever asked for the module -- see
#: :func:`_requested_by_the_console`.
_CONSOLE_DIR = Path(__file__).parent / "console"


#: The standard library's ``importlib`` package directory. Compared as a *path*
#: rather than by the directory's name: a vendored ``somelib/importlib/`` would
#: otherwise be mistaken for the import system's own frames.
_IMPORT_MACHINERY_DIR = os.path.dirname(importlib.__file__)


def _is_import_machinery(filename: str) -> bool:
    """Is this frame the import system's, rather than someone's code?

    A failed import contributes two shapes: the frozen bootstrap modules
    (``<frozen importlib._bootstrap>``), and ``importlib/__init__.py`` when the
    import went through :func:`importlib.import_module`.
    """
    return filename.startswith("<") or os.path.dirname(filename) == _IMPORT_MACHINERY_DIR


#: Frame names the import system itself runs on the importer's behalf: a
#: module executing its own body, and PEP 562's module-level ``__getattr__``,
#: which is how a library spells a lazy submodule.
_IMPORT_SYSTEM_CALLBACKS = frozenset({"<module>", "__getattr__"})


def _requested_by_the_console(exc: BaseException) -> bool:
    """Did the console *import* the module that turned out to be missing?

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

    So the question is asked of the *frames*, in two steps:

    1. Find the innermost frame belonging to the console. No such frame means
       the console had no part in this, and it re-raises.
    2. Ask what the import system ran **directly below** it. Exactly three
       things appear there when the console's own statement asks for a name:
       the import **machinery**, a **module body**, or a module-level
       **``__getattr__``** (PEP 562, how a library spells a lazy submodule).
       Anything else is an ordinary call frame -- the console called a
       function, and the failure is that function's own lazy import.

    Step 2 is the whole discrimination, and it has been wrong twice by
    inspecting the wrong part of the traceback. Both directions matter:

    ===================================== ======================================
    Rule                                  Shape it misreads
    ===================================== ======================================
    deepest frame that is not machinery   ``rich`` installed with its own
                                          ``pygments`` missing: the deepest code
                                          frame is inside ``rich``, so it blames
                                          ``rich`` and re-raises.
    ...and not a module body              a library resolving its imports in a
                                          helper (``def _setup(): import
                                          pygments`` called at module scope, as
                                          ``matplotlib`` does): a *call* frame
                                          sits at the bottom of what is still
                                          the console's import.
    any import evidence anywhere below    over-corrects: a library the console
                                          *called* that does its own
                                          ``importlib.import_module`` leaves a
                                          machinery frame down there, and its
                                          bug becomes "install the extra".
    ===================================== ======================================

    The first two shapes are the same failure -- a **half-installed extra**,
    which ``pip install mfgparams[console]`` repairs and FR-011 exists to
    describe. So is PEP 562, and the ``__getattr__`` marker is what catches it:
    ``from lib import thing`` puts that call frame directly below the console
    with the cascade beneath *it*.

    Both other markers are needed too. CPython elides the
    ``importlib._bootstrap`` frames from a plain failing ``import``, so a module
    body is often the only evidence an import ran at all, while
    ``importlib.import_module`` leaves machinery frames and no module body.

    What is deliberately *not* answered: a library whose import is simply
    **wrong** -- a typo, or an undeclared dependency imported unconditionally.
    Its traceback is identical in shape to the half-installed one, both being
    "the console imported X; something under X was missing", so no rule reading
    frames can separate them. Decided in favour of FR-011, which is a
    requirement, over a clearer diagnostic for a library bug, which is not.

    A ``__getattr__`` reached by *attribute access* rather than by an import
    statement (``import lib`` then ``lib.thing``) is indistinguishable here and
    takes the friendly path too. That is the right answer for the PEP 562 case
    it is there for, and a class's ``__getattr__`` doing a failing import is
    rare enough to accept as the cost.
    """
    frames = []
    traceback = exc.__traceback__
    while traceback is not None:
        code = traceback.tb_frame.f_code
        frames.append((code.co_filename, code.co_name))
        traceback = traceback.tb_next

    console = _CONSOLE_DIR.resolve()
    innermost = None
    for index, (filename, _) in enumerate(frames):
        if _is_import_machinery(filename):
            continue
        # `Path.is_relative_to` is 3.9+, which is this project's floor.
        if Path(filename).resolve().is_relative_to(console):
            innermost = index

    if innermost is None:
        return False

    below = frames[innermost + 1 :]
    if not below:
        return True

    filename, function = below[0]
    return _is_import_machinery(filename) or function in _IMPORT_SYSTEM_CALLBACKS


#: Stands in for the module name when the exception did not carry one (an
#: import hook may omit it). This is user-facing prose inside a user-facing
#: sentence, so Principle VIII puts it in the catalog rather than inline here:
#: spliced in as a literal it would stay English in a translated message.
_UNNAMED_DEPENDENCY_MESSAGE_ID = "console.missing_dependency.unnamed"


def _report_missing_console(module: str | None) -> int:
    """Print the FR-011 message for ``module`` and return the exit status."""
    from mfgparams.i18n import get_locale, translate

    locale = get_locale()
    named = repr(module) if module else translate(locale, _UNNAMED_DEPENDENCY_MESSAGE_ID)
    message = translate(locale, _MISSING_CONSOLE_MESSAGE_ID, module=named)
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
        # Provenance answers "did the console ask for this?", not "can the
        # extra supply it?" -- and inside the console those differ. A missing
        # module of *ours* was requested by the console yet is a damaged
        # install, so it needs the import-time question asked here too;
        # otherwise a lazy `from mfgparams.processes... import x` that failed
        # would be answered with "pip install mfgparams[console]", advice that
        # cannot work (contracts/console-entry-contract.md).
        if _is_broken_core(exc.name) or not _requested_by_the_console(exc):
            raise
        return _report_missing_console(exc.name)

    if status is None:
        return 0
    if isinstance(status, int):
        return status

    # `sys.exit("message")` semantics: a non-int status is a message, not a
    # number. `int()` on it raises ValueError *inside the entry point*,
    # replacing whatever the console was trying to say with a traceback.
    # `bool` is an `int` and takes the branch above, so `return False` exits 0
    # and `return True` exits 1 -- the same quirk `sys.exit` has, kept rather
    # than special-cased so the two agree.
    print(status, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
