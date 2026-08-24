Drilling API reference (developers)
====================================

This page documents the drilling public API and the internal structure of
``machine_calc.operations.drilling`` for contributors adding or extending
drilling behaviour. For end-user CLI guidance see :doc:`drilling`.

Public entry points
--------------------

Both names are importable directly from ``machine_calc``.

``calculate(...)``
    .. code-block:: python

        calculate(
            diameter,
            depth,
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

``list_tools(config_path=None) -> list[str]``
    Names of the available drilling tools, in catalog order.

Length inputs (``diameter``, ``depth``) are interpreted in the caller's
``unit_system``: mm under ``METRIC`` and inches under ``IMPERIAL``. They are
converted to canonical millimetres internally and the results converted
back, so a metric call and the equivalent imperial call describe the same
physical hole. ``available_power`` follows the same per-``unit_system``
convention: kW under ``METRIC``, HP under ``IMPERIAL``.

Results and errors
-------------------

``calculate`` returns a :class:`~machine_calc.models.CalculationResult` and
never raises for an expected validation failure. On success every numeric
field is populated except ``material_removal_rate``, which stays ``None`` —
that field is specific to milling. On failure ``error`` is an
:class:`~machine_calc.models.ErrorInfo` with a stable ``code`` and a
translated ``message``, and every numeric field is ``None``.

Base error codes (``001-metal-drilling-calc``): ``INVALID_DIAMETER``,
``INVALID_DEPTH``, ``MISSING_MATERIAL``, ``MISSING_TOOL``,
``UNUSABLE_MATERIAL``. Calculation-mode error codes
(``002-constrained-calculation-modes``, see "Calculation modes" below):
``INVALID_TARGET_RPM``, ``MODE_CONFLICT``, ``INFEASIBLE_POWER_BUDGET``.
``INVALID_AVAILABLE_POWER`` was introduced later, by
``010-milling-calculation-modes`` (operation-agnostic validation shared
with milling — see its spec's Key Decisions), but the shared
``validate_mode_arguments()`` applies it to drilling's ``STANDARD``/
``FIXED_RPM`` modes too.

Validation runs in a fixed order, so a call with several invalid inputs
always reports the same first failure: material and tool presence are
checked first, then the material and tool are resolved, then the geometry
(diameter, depth), then — last — the ``mode``/``target_rpm`` combination.

``diameter`` and ``depth`` must each be a positive, finite number within
the configured bound. ``NaN``, ``+inf``/``-inf`` and non-numeric values
return ``INVALID_DIAMETER``/``INVALID_DEPTH`` rather than passing
validation or raising from the bound comparison (issue #56) — the same
posture the milling validators and ``validate_target_rpm()`` already
applied.

Calculation modes
-------------------

``calculate`` accepts ``mode``/``target_rpm``/``available_power`` arguments,
added by ``002-constrained-calculation-modes``. Milling's entry points
(:func:`~machine_calc.calculate_end_milling`,
:func:`~machine_calc.calculate_face_milling`) accept the identical set,
reusing this same contract.

``CalculationMode.STANDARD`` (default)
    Unconstrained calculation, unchanged from ``001-metal-drilling-calc``.
    ``available_power`` remains optional/advisory: an exceeded budget sets
    ``feasibility_warning`` without altering the result. A supplied but
    non-numeric, non-finite, or non-positive ``available_power`` returns
    ``INVALID_AVAILABLE_POWER``; ``None`` (omitted) is always valid.

``CalculationMode.POWER_CONSTRAINED``
    ``available_power`` becomes **required**: a missing value (``None``)
    returns ``MODE_CONFLICT``, the same as also supplying ``target_rpm`` in
    this mode. A *supplied but invalid* (non-numeric, non-finite, zero, or
    negative) ``available_power`` returns ``INFEASIBLE_POWER_BUDGET``. The
    result is a no-op (identical to STANDARD, only ``mode`` differs) when
    ``available_power`` is at least the STANDARD-mode power requirement,
    **or** within ``math.isclose(rel_tol=1e-9)`` of it even from slightly
    below — the no-op boundary is that tolerance band, not a hard ``>=``
    cutoff. Only when the budget falls clearly short of that band is the
    spindle speed actually reduced, algebraically, so that
    ``power_required`` matches ``available_power`` exactly; torque is
    unaffected, since it does not depend on spindle speed — this
    closed-form, non-iterative derivation is what makes the adjustment a
    single algebraic step rather than a search.

``CalculationMode.FIXED_RPM``
    ``target_rpm`` becomes **required** and is echoed back exactly as
    ``spindle_speed_rpm``; every dependent field is recomputed at that
    spindle speed. ``available_power`` stays optional/advisory here too,
    with the same ``INVALID_AVAILABLE_POWER`` check as ``STANDARD`` mode's
    advisory power. A missing, non-numeric, non-positive or non-finite
    ``target_rpm`` returns ``INVALID_TARGET_RPM``.

    .. note::
        ``validate_target_rpm()`` only checks positivity and finiteness, not
        a practical lower bound: an extreme subnormal value (e.g.
        ``5e-324``) currently passes validation but underflows the feed-rate
        calculation to zero and raises ``ZeroDivisionError`` in
        ``calculate_drilling_metrics_at_rpm()``, contradicting
        ``calculate()``'s documented never-raises contract. Tracked as a
        pre-existing bug in issue #55, not something this drilling
        documentation PR introduces or fixes.

Supplying both ``target_rpm`` and ``POWER_CONSTRAINED`` mode is rejected as
``MODE_CONFLICT`` rather than silently picking one.

Package layout
---------------

.. code-block:: text

    machine_calc/operations/drilling/
        __init__.py         calculate() and its validate/convert/assemble orchestration
        formulas.py          calculate_drilling_metrics / calculate_drilling_metrics_at_rpm /
                              calculate_power_constrained_metrics
        tools.py              DrillingTool registry
        data/tools.toml       bundled drill-tool catalog (HSS, Cobalt, Carbide)

Unlike milling, drilling has a single sub-operation, so it needs no shared
orchestration layer analogous to milling's ``_calculate.py`` — ``__init__.py``
implements ``calculate()`` directly, delegating geometry/mode validation to
:mod:`machine_calc.validation` and metrics computation to ``formulas.py``.

Formulas
--------

``formulas.py`` implements, in order: cutting speed to spindle speed
(``calculate_drilling_metrics``), feed rate from spindle speed and feed per
revolution, machining time from hole depth plus a point-engagement
allowance for the drill's cutting point, torque from the specific cutting
force (k\ :sub:`c`) and feed per revolution — independent of spindle speed
— and power from torque and spindle speed
(``calculate_drilling_metrics_at_rpm``). ``calculate_power_constrained_metrics``
reuses the fact that torque is independent of spindle speed to solve for
the reduced spindle speed algebraically rather than iteratively. Sources
are cited per function; see ``specs/001-metal-drilling-calc/research.md``
and ``specs/002-constrained-calculation-modes/research.md`` for the
decisions behind them.
