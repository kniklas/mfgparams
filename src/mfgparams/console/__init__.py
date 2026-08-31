"""Interactive console for mfgparams -- presentation only.

This sub-package holds the REPL: prompting, formatting, and the process/
operation menus. It owns no calculation logic; everything numeric lives under
:mod:`mfgparams.processes`.

**The calculation core MUST NOT import this package**, at module import time
or otherwise. The dependency runs one way: the console imports the core, never
the reverse. Keeping it one-way is what lets ``pip install mfgparams`` carry
only what the calculations need, with the console's dependencies behind the
``console`` extra.

The single exemption is ``mfgparams/__main__.py``, which the interpreter
requires at the package root for ``python -m mfgparams``; its import of this
package is inside the function body, never at module scope. Both halves of the
rule are enforced by ``tests/static/test_core_does_not_import_console.py``
rather than by convention (FR-008).
"""
