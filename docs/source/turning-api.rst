Turning API reference (developers)
====================================

This page documents the turning public API and the internal structure of
``mfgparams.processes.machining.turning`` for contributors adding or
extending turning behaviour. For end-user text-GUI guidance see
:doc:`turning`.

Public entry points
--------------------

Both names are importable directly from ``mfgparams``.

``calculate_turning(...)``
    .. code-block:: python

        calculate_turning(
            diameter,
            depth_of_cut,
            length_of_cut,
            material,
            tool,
            unit_system=UnitSystem.METRIC,
            available_power=None,
            config_path=None,
            locale="en",
            mode=CalculationMode.STANDARD,
            target_rpm=None,
            materials_config_path=None,
        ) -> CalculationResult

``list_turning_tools(config_path=None) -> list[str]``
    Names of the available turning tools, in catalog order.

Length inputs (``diameter``, ``depth_of_cut``, ``length_of_cut``) are
interpreted in the caller's ``unit_system``: mm under ``METRIC`` and inches
under ``IMPERIAL``. They are converted to canonical millimetres internally
and the results converted back. ``available_power`` follows the same
per-``unit_system`` convention: kW under ``METRIC``, HP under ``IMPERIAL``.
``cutting_force`` (the newest result field) is reported in newtons under
``METRIC`` and lbf under ``IMPERIAL``.

Results and errors
-------------------

``calculate_turning`` returns a :class:`~mfgparams.models.CalculationResult`
and never raises for an expected validation failure. On success every
numeric field is populated, including the ``cutting_force`` field this
feature introduces; ``material_removal_rate`` stays ``None`` (that field
is specific to milling). On failure ``error`` is an
:class:`~mfgparams.models.ErrorInfo` with a stable ``code`` and a
translated ``message``, and every numeric field — including
``cutting_force`` — is ``None``.

Error codes: turning introduces zero new error codes. Every validation
failure reuses an existing one — ``INVALID_DIAMETER``,
``INVALID_DEPTH_OF_CUT`` (including a depth-of-cut-exceeds-workpiece-radius
case, a new *message* under the same code), ``INVALID_LENGTH_OF_CUT``
(reused verbatim from milling's own ``length_of_cut`` input),
``MISSING_MATERIAL``, ``MISSING_TOOL``, ``UNUSABLE_MATERIAL``,
``INVALID_TARGET_RPM``, ``MODE_CONFLICT``, and ``INFEASIBLE_POWER_BUDGET``.

Validation runs in the same fixed order as drilling: material and tool
presence, then resolution, then geometry (diameter, then depth of cut —
including the radius check — then length of cut), then — last — the
``mode``/``target_rpm`` combination.

Each of ``validate_turning_diameter_mm``, ``validate_turning_depth_of_cut_mm``,
and ``validate_turning_length_of_cut_mm`` (in :mod:`mfgparams.validation`)
checks its own turning-specific ``Configuration`` bound
(``max_turning_diameter_mm``, ``max_turning_depth_of_cut_mm``,
``max_turning_length_of_cut_mm``) — distinct fields from drilling's and
milling's own bounds, following the exact precedent
``validate_mill_diameter_mm``/``max_mill_diameter_mm`` already set
alongside drilling's ``validate_diameter_mm``/``max_diameter_mm``.

Calculation modes
-------------------

``calculate_turning`` accepts the identical ``mode``/``target_rpm``/
``available_power`` contract drilling's and milling's entry points do (see
:doc:`drilling-api`'s "Calculation modes" section for the full
description). The only turning-specific detail: cutting force (like
torque) is independent of spindle speed, so ``POWER_CONSTRAINED`` mode's
closed-form, non-iterative spindle-speed reduction carries over unchanged
from drilling's derivation, and ``FIXED_RPM`` mode's ``cutting_force`` and
``torque`` values are identical to standard mode's for the same geometry.

Package layout
---------------

.. code-block:: text

    mfgparams/processes/machining/turning/
        __init__.py         calculate_turning() and its validate/convert/assemble orchestration
        formulas.py          calculate_turning_metrics / calculate_turning_metrics_at_rpm /
                              calculate_turning_power_constrained_metrics
        tools.py              TurningTool registry
        data/tools.toml       bundled turning-tool catalog (HSS, Cobalt, Carbide)

Like drilling, turning has a single sub-operation, so it needs no shared
orchestration layer analogous to milling's ``_calculate.py`` —
``__init__.py`` implements ``calculate_turning()`` directly, mirroring
``processes/machining/drilling/__init__.py``'s shape.

Formulas
--------

``formulas.py`` implements, in order: cutting speed to spindle speed
(``calculate_turning_metrics``), feed rate from spindle speed and feed per
revolution, machining time from length of cut and feed rate (no
point-engagement allowance — a single-point turning tool has no drill-point
geometry to account for), cutting force from the specific cutting force
(k\ :sub:`c`), depth of cut, and feed per revolution — independent of
spindle speed — torque from cutting force acting at the workpiece radius,
and power from torque and spindle speed
(``calculate_turning_metrics_at_rpm``). ``calculate_turning_power_constrained_metrics``
reuses the fact that torque is independent of spindle speed to solve for
the reduced spindle speed algebraically, byte-for-byte the same derivation
drilling's ``calculate_power_constrained_metrics`` uses. Sources are cited
per function; see ``specs/019-turning-calculations/research.md`` for the
decisions behind them.
