mfgparams documentation
===========================

Metal machining calculation library and interactive CLI, covering drilling
(twist drills) and milling (end milling and face milling).

Drilling support (twist drills, plus the standard/power-constrained/
fixed-RPM calculation modes) is covered in:

- ``specs/001-metal-drilling-calc/spec.md``
- ``specs/001-metal-drilling-calc/quickstart.md``
- ``specs/002-constrained-calculation-modes/spec.md``
- ``specs/002-constrained-calculation-modes/quickstart.md``

Wood-materials support (hardwood/softwood/engineered) is covered in:

- ``specs/007-wood-materials-support/spec.md``
- ``specs/007-wood-materials-support/quickstart.md``

Materials are grouped by material type (``metal``, ``wood``, and any further
type declared in a materials config file), and the CLI selects a type before
a specific material. See:

- ``specs/008-material-categorization/spec.md``
- ``specs/005-configurable-materials-tools/contracts/materials-config-schema.md``

Milling support (end milling and face milling, with operation selection in
the REPL) is covered in:

- ``specs/009-milling-calculations/spec.md``
- ``specs/009-milling-calculations/quickstart.md``

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   drilling
   drilling-api
   milling
   milling-api

Indices and tables
===================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. Validation scratch: docs-only change to exercise US1 skip behavior.
