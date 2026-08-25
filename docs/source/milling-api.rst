Milling API reference (developers)
==================================

This page documents the milling public API and the internal structure of
``mfgparams.operations.milling`` for contributors adding or extending
milling behaviour. For end-user CLI guidance see :doc:`milling`.

Public entry points
-------------------

All four names are importable directly from ``mfgparams``.

``calculate_end_milling(...)``
    .. code-block:: python

        calculate_end_milling(
            diameter,
            axial_depth_of_cut,
            radial_depth_of_cut,
            feed_per_tooth,
            number_of_teeth,
            length_of_cut,
            material,
            tool,
            unit_system=UnitSystem.METRIC,
            available_power=None,
            config_path=None,
            locale="en",
            materials_config_path=None,
            mode=CalculationMode.STANDARD,
            target_rpm=None,
        ) -> CalculationResult

``calculate_face_milling(...)``
    Identical, except that ``radial_depth_of_cut`` is named ``width_of_cut``.

``list_end_mill_tools(config_path=None) -> list[str]``
    Names of the available end-mill tools, in catalog order.

``list_face_mill_tools(config_path=None) -> list[str]``
    Names of the available face-mill tools, in catalog order.

Length inputs (``diameter``, the depths/width, ``feed_per_tooth`` and
``length_of_cut``) are interpreted in the caller's ``unit_system``: mm under
``METRIC`` and inches under ``IMPERIAL``. They are converted to canonical
millimetres internally and the results converted back, so a metric call and
the equivalent imperial call describe the same physical cut.

Results and errors
------------------

Both functions return a :class:`~mfgparams.models.CalculationResult` and
never raise for an expected validation failure. On success every numeric
field is populated, including ``material_removal_rate`` (cm³/min under
metric, in³/min under imperial). On failure ``error`` is an
:class:`~mfgparams.models.ErrorInfo` with a stable ``code`` and a
translated ``message``, and every numeric field — including
``material_removal_rate`` — is ``None``.

Error codes reused from drilling: ``INVALID_DIAMETER``,
``MISSING_MATERIAL``, ``MISSING_TOOL``, ``UNUSABLE_MATERIAL``. Codes specific
to milling: ``INVALID_DEPTH_OF_CUT``, ``INVALID_ENGAGEMENT``,
``INVALID_FEED_PER_TOOTH``, ``INVALID_TOOTH_COUNT``,
``INVALID_LENGTH_OF_CUT``. Codes reused from drilling's calculation modes
(``002-constrained-calculation-modes``): ``INFEASIBLE_POWER_BUDGET``,
``INVALID_TARGET_RPM``, ``MODE_CONFLICT`` (see "Calculation modes" below).
Two codes are new in ``010-milling-calculation-modes``:
``INVALID_AVAILABLE_POWER`` (a non-numeric, non-finite, or non-positive
``available_power`` supplied as the optional advisory value in
``STANDARD`` or ``FIXED_RPM`` mode — see "Calculation modes" below for
the distinct ``POWER_CONSTRAINED`` error mapping) and
``CALCULATION_OVERFLOW`` (an otherwise-valid extreme input that overflows
an intermediate calculation).

Validation runs in a fixed order, so a call with several invalid inputs
always reports the same first failure. ``material`` and ``tool`` presence are
checked first, then the material and tool are resolved, then the geometry,
then — last — the ``mode``/``target_rpm`` combination.

Calculation modes
------------------

Both entry points accept the same ``mode``/``target_rpm``/``available_power``
arguments as :func:`mfgparams.calculate` (drilling), added by
``010-milling-calculation-modes``:

``CalculationMode.STANDARD`` (default)
    Unconstrained calculation, unchanged from ``009-milling-calculations``.
    ``available_power`` remains optional/advisory: an exceeded budget sets
    ``feasibility_warning`` without altering the result. A supplied but
    non-numeric, non-finite, or non-positive ``available_power`` returns
    ``INVALID_AVAILABLE_POWER``; ``None`` (omitted) is always valid.

``CalculationMode.POWER_CONSTRAINED``
    ``available_power`` becomes **required**: a missing value (``None``)
    returns ``MODE_CONFLICT``, the same as also supplying ``target_rpm``
    in this mode. A *supplied but invalid* (non-numeric, non-finite,
    zero, or negative) ``available_power`` returns
    ``INFEASIBLE_POWER_BUDGET`` — not ``INVALID_AVAILABLE_POWER``, which
    is reserved for the advisory-power path in ``STANDARD``/``FIXED_RPM``
    — since no spindle speed could ever meet it either way. If it is at
    least the STANDARD-mode power requirement the result is a no-op
    (identical to STANDARD, only ``mode`` differs). Otherwise the spindle
    speed is reduced so that ``power_required`` matches
    ``available_power`` exactly (within ``math.isclose(rel_tol=1e-9)``);
    torque is unaffected, since it does not depend on spindle speed. An
    otherwise-valid extreme input that overflows an intermediate
    calculation returns ``CALCULATION_OVERFLOW``.

``CalculationMode.FIXED_RPM``
    ``target_rpm`` becomes **required** and is echoed back exactly as
    ``spindle_speed_rpm``; every dependent field is recomputed at that
    spindle speed. ``available_power`` stays optional/advisory here too,
    with the same ``INVALID_AVAILABLE_POWER`` check as ``STANDARD``
    mode's advisory power. A missing, non-numeric, non-positive or
    non-finite ``target_rpm`` returns ``INVALID_TARGET_RPM``. An
    otherwise-valid extreme input that overflows an intermediate
    calculation returns ``CALCULATION_OVERFLOW``.

Supplying both ``target_rpm`` and ``POWER_CONSTRAINED`` mode is rejected as
``MODE_CONFLICT`` (FR-009) rather than silently picking one.

Package layout
--------------

.. code-block:: text

    mfgparams/operations/milling/
        _shared.py          formulas common to both sub-operations
        _tool_registry.py   MillingTool base + build_registry()
        _calculate.py       shared validate/convert/assemble orchestration
        end_milling/
            __init__.py     calculate_end_milling / list_end_mill_tools
            formulas.py     EndMillingMetrics wrapper over _shared
            tools.py        EndMillTool registry
            data/tools.toml bundled end-mill catalog
        face_milling/       same shape, for face milling

Both sub-operations are peers: neither imports the other, and neither imports
``operations.drilling``. Everything shared between operations lives in the
top-level modules (``config``, ``models``, ``units``, ``validation``,
``registry``, ``i18n``). This boundary is enforced statically by
``tests/contract/test_library_api_milling.py``.

``_calculate.calculate_milling()`` holds the single copy of the validation,
unit-conversion and result-assembly sequence. It stays generic over the two
sub-operations by taking four injection points:

``resolve_tool``
    Looks a tool name up in that sub-operation's registry.

``compute``
    The sub-operation's own ``formulas.py`` adapter. Routing through it — not
    straight to ``_shared`` — is what keeps each sub-operation's module
    boundary meaningful, so a sub-operation can diverge from the shared model
    without touching the other.

``engagement_label_key``
    The message-catalog key naming the radial input, so validation errors say
    "Radial depth of cut" for end milling and "Width of cut" for face
    milling.

``compute_at_rpm``
    The sub-operation's ``formulas.py`` at-RPM adapter, used instead of
    ``compute`` when ``mode`` is ``POWER_CONSTRAINED`` or ``FIXED_RPM``
    (``010-milling-calculation-modes``), so each sub-operation supplies its
    own fixed-spindle-speed metrics rather than sharing one implementation
    across both.

The ``compute`` callable returns anything satisfying the
``MillingMetricsLike`` protocol. Its members are declared as read-only
properties because the concrete metrics types are frozen dataclasses.

Adding a milling sub-operation
------------------------------

1. Create ``operations/milling/<name>/`` with ``__init__.py``,
   ``formulas.py``, ``tools.py`` and ``data/tools.toml``.
2. Give the TOML catalog a **table key unique across all operations**
   (drilling uses ``tools``, end milling ``end_mill_tools``, face milling
   ``face_mill_tools``). Reusing another operation's key will make that
   operation's loader try to parse your entries.
3. Register the data file in ``pyproject.toml``'s
   ``[tool.setuptools.package-data]``.
4. Build the registry with ``_tool_registry.build_registry()`` and implement
   ``formulas.py`` as a thin adapter over ``_shared``.
5. Implement the entry point by delegating to ``_calculate.calculate_milling()``
   with your ``resolve_tool``, ``compute`` and ``engagement_label_key``.
6. Add the sub-operation to ``MillingSubOperation``, add its prompts to the
   message catalog, and wire a session function into ``cli.py``.
7. Re-export the entry point from ``mfgparams/__init__.py``.

Every user-facing string must be a catalog key, and every formula must cite
its source in a docstring.

Formulas
--------

``_shared.py`` implements, in order: cutting speed to spindle speed, feed
rate from feed per tooth and tooth count, machining time from length of cut,
material removal rate from the engaged cross-section and feed rate, cutting
power from the specific cutting force (k\ :sub:`c`) and removal rate, and
torque from power and spindle speed. The engagement model is full and
symmetric, with no radial chip-thinning compensation. Sources are cited per
function; see ``specs/009-milling-calculations/research.md`` for the
decisions behind them.
