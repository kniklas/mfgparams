"""Entry point for ``python -m mfgparams.console``.

Runs the interactive console directly, bypassing the package-root guard in
``mfgparams/__main__.py``. Useful when you want the raw import error rather
than the friendly missing-dependency message -- the guard exists for end
users, not for debugging a broken console install.
"""

from __future__ import annotations

from mfgparams.console.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
