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

For metal materials, the text GUI's Material field opens a dedicated
selection window offering three independently-searchable identifiers side
by side (common name, EN material number, shortened/DIN-style designation).
A materials config file may add ``material_number``/``short_notation`` to a
``[[materials]]`` entry to make it searchable by those identifiers too. See:

- ``specs/023-material-selector-dialog/spec.md``
- ``specs/023-material-selector-dialog/contracts/materials-config-schema-delta.md``

Milling support (end milling and face milling, with operation selection in
the text GUI) is covered in:

- ``specs/009-milling-calculations/spec.md``
- ``specs/009-milling-calculations/quickstart.md``

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   drilling
   drilling-api
   milling
   milling-api
   turning
   turning-api

Indices and tables
===================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
