"""Entry point for ``python -m mfgparams.console``.

Delegates to the package-root :func:`mfgparams.__main__.main` rather than
calling the console directly, so this form is guarded exactly like the other
two. FR-011 is unqualified -- *invoking the console* when its dependencies are
unavailable must produce the actionable message and never a stack trace -- and
this is a form a user reaches by guessing, not one reserved for maintainers.
An earlier version called ``console.cli.main`` straight through, on the
reasoning that a bypass is useful for debugging a broken console install; that
made one of the three ways to start the console behave differently from the
other two, with nothing to tell a user which one they had picked.

Debugging the raw import error is still one line, and an explicit one:
``python -c "from mfgparams.console.cli import main; main()"``.
"""

from __future__ import annotations

from mfgparams.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
