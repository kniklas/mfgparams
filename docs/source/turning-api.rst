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
            target_feed_rate=None,
        ) -> CalculationResult

``list_turning_tools(config_path=None) -> list[str]``
    Names of the available turning tools, in catalog order.

Length inputs (``diameter``, ``depth_of_cut``, ``length_of_cut``,
``target_feed_rate``) are interpreted in the caller's ``unit_system``: mm
(mm/rev for ``target_feed_rate``) under ``METRIC`` and inches (in/rev)
under ``IMPERIAL``. They are converted to canonical millimetres internally
and the results converted back. ``available_power`` follows the same
per-``unit_system`` convention: kW under ``METRIC``, HP under ``IMPERIAL``.
``cutting_force`` is reported in newtons under ``METRIC`` and lbf under
``IMPERIAL``; ``feed_per_rotation`` (specs/020-turning-feed-per-rotation)
in mm/rev under ``METRIC`` and in/rev under ``IMPERIAL``.

Results and errors
-------------------

``calculate_turning`` returns a :class:`~mfgparams.models.CalculationResult`
and never raises for an expected validation failure. On success every
numeric field is populated, including ``cutting_force`` and
``feed_per_rotation``; ``material_removal_rate`` stays ``None`` (that field
is specific to milling). ``feed_per_rotation`` is purely additive: it does
not change ``feed_rate``'s own meaning or value, which stay exactly as
they were before this field existed. On failure ``error`` is an
:class:`~mfgparams.models.ErrorInfo` with a stable ``code`` and a
translated ``message``, and every numeric field — including
``cutting_force`` and ``feed_per_rotation`` — is ``None``.

Error codes: turning has one turning-specific error code beyond what it
originally shipped with — ``INVALID_TARGET_FEED_RATE`` (a supplied
``target_feed_rate`` that is zero, negative, non-numeric, or non-finite, or
missing when ``mode is FEED_RATE_CONSTRAINED``). Every other validation
failure reuses an existing code — ``INVALID_DIAMETER``,
``INVALID_DEPTH_OF_CUT`` (including a depth-of-cut-exceeds-workpiece-radius
case, a new *message* under the same code), ``INVALID_LENGTH_OF_CUT``
(reused verbatim from milling's own ``length_of_cut`` input),
``MISSING_MATERIAL``, ``MISSING_TOOL``, ``UNUSABLE_MATERIAL``,
``INVALID_TARGET_RPM``, ``MODE_CONFLICT``, and ``INFEASIBLE_POWER_BUDGET``.
``MODE_CONFLICT`` also covers supplying ``target_feed_rate`` together with
``target_rpm``, or together with any mode other than
``FEED_RATE_CONSTRAINED``.

Validation runs in the same fixed order as drilling: material and tool
presence, then resolution, then geometry (diameter, then depth of cut —
including the radius check — then length of cut), then — last — the
``mode``/``target_rpm``/``target_feed_rate`` combination.

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

Turning also has a fourth mode, ``CalculationMode.FEED_RATE_CONSTRAINED``
(specs/020-turning-feed-per-rotation), which only ``calculate_turning``
implements. Drilling's and milling's own dispatch never construct this
member, but since it lives on the shared ``CalculationMode`` enum, a
caller can still pass it directly to ``calculate()``/
``calculate_end_milling()``/``calculate_face_milling()`` — both explicitly
reject it with a structured ``UNSUPPORTED_MODE`` error rather than
silently falling through to a standard-mode result mislabeled with this
mode. In turning, it derives spindle speed exactly as ``STANDARD``
(from cutting speed and diameter), then computes every dependent metric
from the caller-supplied ``target_feed_rate`` instead of the material/
tool's reference feed value — so, unlike ``FIXED_RPM``'s ``cutting_force``/
``torque`` (unchanged from the nominal value), this mode's ``cutting_force``,
``torque``, and ``power_required`` **do** change, since turning's cutting
force depends directly on feed per revolution (``Fc = Kc * ap * fn``).

Package layout
---------------

.. code-block:: text

    mfgparams/processes/machining/turning/
        __init__.py         calculate_turning() and its validate/convert/assemble orchestration
        formulas.py          calculate_turning_metrics / calculate_turning_metrics_at_rpm /
                              calculate_turning_power_constrained_metrics /
                              calculate_turning_feed_rate_constrained_metrics
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
drilling's ``calculate_power_constrained_metrics`` uses.
``calculate_turning_feed_rate_constrained_metrics`` derives spindle speed
the same way, then calls ``calculate_turning_metrics_at_rpm`` with an
explicit ``feed_per_rev_mm`` override instead of letting it derive that
value from the material/tool — the same helper every other mode uses,
extended with one optional parameter rather than duplicated. Sources are
cited per function; see ``specs/019-turning-calculations/research.md`` and
``specs/020-turning-feed-per-rotation/research.md`` for the decisions
behind them.
