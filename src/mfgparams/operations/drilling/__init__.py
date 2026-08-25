"""Drilling operation: public entry point (FR-001 through FR-018).

Re-exported at the top level as ``mfgparams.calculate`` since drilling is
currently the module's only operation (contracts/library-api.md). Future
operations (turning, milling, ...) add their own sibling
``mfgparams.operations.<operation>`` module with an analogous
``calculate()`` without changing this contract.
"""

from __future__ import annotations

import math

from mfgparams.config import load_configuration
from mfgparams.i18n import DEFAULT_LOCALE, translate
from mfgparams.models import CalculationMode, CalculationResult, ErrorInfo, UnitSystem
from mfgparams.registry import get_material, get_material_validation
from mfgparams.units import (
    hp_to_kw,
    kw_to_hp,
    mm_to_in,
    nm_to_in_lb,
    to_metric_length,
)
from mfgparams.validation import (
    validate_depth_mm,
    validate_diameter_mm,
    validate_material_present,
    validate_mode_arguments,
    validate_target_rpm,
    validate_tool_present,
)

from .formulas import (
    calculate_drilling_metrics,
    calculate_drilling_metrics_at_rpm,
    calculate_power_constrained_metrics,
)
from .tools import get_tool


def _error_result(
    unit_system: UnitSystem, error: ErrorInfo, mode: CalculationMode = CalculationMode.STANDARD
) -> CalculationResult:
    return CalculationResult(
        spindle_speed_rpm=None,
        feed_rate=None,
        machining_time=None,
        torque=None,
        power_required=None,
        unit_system=unit_system,
        feasibility_warning=None,
        error=error,
        mode=mode,
    )


def _compute_metrics(
    mode: CalculationMode,
    diameter_mm: float,
    depth_mm: float,
    resolved_material,
    resolved_tool,
    available_power_kw: float | None,
    target_rpm: float | None,
    unit_system: UnitSystem,
    locale: str,
):
    """Dispatch to the mode-specific metrics calculation.

    Returns a :class:`~mfgparams.operations.drilling.formulas.DrillingMetrics`
    on success, or a :class:`CalculationResult` carrying an
    ``INFEASIBLE_POWER_BUDGET`` error if ``POWER_CONSTRAINED`` mode cannot
    produce a feasible result. Extracted from ``calculate()`` to keep that
    function's cyclomatic complexity/Maintainability Index within the
    thresholds configured in ``pyproject.toml`` (FR-001/FR-002).
    """
    if mode is CalculationMode.POWER_CONSTRAINED:
        # available_power_kw is guaranteed non-None here (validate_mode_arguments
        # rejects POWER_CONSTRAINED without it as MODE_CONFLICT).
        assert available_power_kw is not None
        if available_power_kw <= 0:
            return _error_result(
                unit_system,
                ErrorInfo(
                    "INFEASIBLE_POWER_BUDGET",
                    translate(locale, "error.infeasible_power_budget"),
                ),
                mode,
            )
        metrics = calculate_power_constrained_metrics(
            diameter_mm, depth_mm, resolved_material, resolved_tool, available_power_kw
        )
        if not math.isfinite(metrics.spindle_speed_rpm) or metrics.spindle_speed_rpm <= 0:
            return _error_result(
                unit_system,
                ErrorInfo(
                    "INFEASIBLE_POWER_BUDGET",
                    translate(locale, "error.infeasible_power_budget"),
                ),
                mode,
            )
        return metrics

    if mode is CalculationMode.FIXED_RPM:
        # target_rpm is guaranteed non-None here (INVALID_TARGET_RPM is
        # returned earlier in calculate() when it is None for this mode).
        assert target_rpm is not None
        return calculate_drilling_metrics_at_rpm(
            diameter_mm, depth_mm, resolved_material, resolved_tool, target_rpm
        )

    return calculate_drilling_metrics(diameter_mm, depth_mm, resolved_material, resolved_tool)


def _resolve_material_and_tool(
    material: str,
    tool: str,
    unit_system: UnitSystem,
    locale: str,
    mode: CalculationMode,
    materials_config_path: str | None = None,
):
    """Validate and resolve the material/tool names to their registry entries.

    Returns a :class:`CalculationResult` if either is invalid/unknown, or
    the tuple ``(resolved_material, resolved_tool)`` on success. Extracted
    from ``_validate_and_prepare`` to keep it within the cyclomatic
    complexity/Maintainability Index thresholds configured in
    ``pyproject.toml`` (FR-001/FR-002).

    Args:
        materials_config_path: Optional path to a user-supplied
            materials/tools configuration file (FR-002 of
            005-configurable-materials-tools); unrelated to the
            validation-bounds ``config_path`` (FR-017).
    """
    material_error = validate_material_present(material, locale)
    if material_error:
        return _error_result(unit_system, material_error, mode)

    tool_error = validate_tool_present(tool, locale)
    if tool_error:
        return _error_result(unit_system, tool_error, mode)

    resolved_material = get_material(material, materials_config_path)
    if resolved_material is None:
        return _error_result(
            unit_system,
            ErrorInfo(
                "MISSING_MATERIAL",
                translate(locale, "error.unknown_material", material=material),
            ),
            mode,
        )
    validation = get_material_validation(material, materials_config_path)
    if validation is not None and validation.status == "warning":
        details = "; ".join(validation.issues)
        return _error_result(
            unit_system,
            ErrorInfo(
                "UNUSABLE_MATERIAL",
                translate(
                    locale,
                    "error.unusable_material",
                    material=material,
                    details=details,
                ),
            ),
            mode,
        )

    resolved_tool = get_tool(tool, materials_config_path)
    if resolved_tool is None:
        return _error_result(
            unit_system,
            ErrorInfo("MISSING_TOOL", translate(locale, "error.unknown_tool", tool=tool)),
            mode,
        )

    return resolved_material, resolved_tool


def _validate_geometry(
    diameter: float,
    depth: float,
    unit_system: UnitSystem,
    config,
    locale: str,
    mode: CalculationMode,
):
    """Convert diameter/depth to metric and validate them.

    Returns a :class:`CalculationResult` if invalid, or the tuple
    ``(diameter_mm, depth_mm)`` on success. Extracted from
    ``_validate_and_prepare`` to keep it within the cyclomatic
    complexity/Maintainability Index thresholds configured in
    ``pyproject.toml`` (FR-001/FR-002).
    """
    # to_metric_length() (not a bare in_to_mm() call) so a non-numeric or
    # bool length is passed through unconverted and rejected by the
    # validators below as INVALID_DIAMETER/INVALID_DEPTH, rather than
    # raising TypeError from the multiplication inside in_to_mm() before
    # validation runs — milling already routed its imperial inputs through
    # this guard (issue #56 review follow-up).
    diameter_mm = to_metric_length(diameter, unit_system)
    depth_mm = to_metric_length(depth, unit_system)

    diameter_error = validate_diameter_mm(diameter_mm, config, locale)
    if diameter_error:
        return _error_result(unit_system, diameter_error, mode)

    depth_error = validate_depth_mm(depth_mm, config, locale)
    if depth_error:
        return _error_result(unit_system, depth_error, mode)

    return diameter_mm, depth_mm


def _validate_mode_inputs(
    mode: CalculationMode,
    available_power: float | None,
    target_rpm: float | None,
    unit_system: UnitSystem,
    locale: str,
):
    """Validate the mode-specific arguments (``target_rpm``/``available_power``).

    Returns a :class:`CalculationResult` if invalid, or ``None`` on success.
    Extracted from ``_validate_and_prepare`` to keep it within the
    cyclomatic complexity/Maintainability Index thresholds configured in
    ``pyproject.toml`` (FR-001/FR-002).
    """
    # Mode-argument validation runs only after the base spec's existing
    # material/tool/diameter/depth checks — unchanged order/precedence
    # (/speckit.analyze finding U1; data-model.md Validation order).
    if mode is CalculationMode.FIXED_RPM:
        target_rpm_error = validate_target_rpm(target_rpm, locale)
        if target_rpm_error:
            return _error_result(unit_system, target_rpm_error, mode)
        if target_rpm is None:
            return _error_result(
                unit_system,
                ErrorInfo("INVALID_TARGET_RPM", translate(locale, "error.invalid_target_rpm")),
                mode,
            )

    return (
        _error_result(unit_system, mode_error, mode)
        if (mode_error := validate_mode_arguments(mode, available_power, target_rpm, locale))
        else None
    )


def _validate_and_prepare(
    diameter: float,
    depth: float,
    material: str,
    tool: str,
    unit_system: UnitSystem,
    available_power: float | None,
    config_path: str | None,
    locale: str,
    mode: CalculationMode,
    target_rpm: float | None,
    materials_config_path: str | None = None,
):
    """Validate all inputs and resolve/convert them for calculation.

    Returns a :class:`CalculationResult` if any validation fails, or a tuple
    ``(resolved_material, resolved_tool, diameter_mm, depth_mm,
    available_power_kw)`` on success. Extracted from ``calculate()`` to keep
    that function's cyclomatic complexity/Maintainability Index within the
    thresholds configured in ``pyproject.toml`` (FR-001/FR-002).
    """
    config = load_configuration(config_path)

    resolved = _resolve_material_and_tool(
        material, tool, unit_system, locale, mode, materials_config_path
    )
    if isinstance(resolved, CalculationResult):
        return resolved
    resolved_material, resolved_tool = resolved

    geometry = _validate_geometry(diameter, depth, unit_system, config, locale, mode)
    if isinstance(geometry, CalculationResult):
        return geometry
    diameter_mm, depth_mm = geometry

    mode_input_error = _validate_mode_inputs(mode, available_power, target_rpm, unit_system, locale)
    if mode_input_error is not None:
        return mode_input_error

    available_power_kw = None
    if available_power is not None:
        available_power_kw = (
            hp_to_kw(available_power) if unit_system is UnitSystem.IMPERIAL else available_power
        )

    return resolved_material, resolved_tool, diameter_mm, depth_mm, available_power_kw


def _build_result(
    metrics,
    unit_system: UnitSystem,
    available_power_kw: float | None,
    mode: CalculationMode,
    locale: str,
) -> CalculationResult:
    """Apply unit conversion, the feasibility-warning check, and build the
    final success :class:`CalculationResult`. Extracted from ``calculate()``
    to keep that function's cyclomatic complexity/Maintainability Index
    within the thresholds configured in ``pyproject.toml`` (FR-001/FR-002).
    """
    feasibility_warning = None
    if available_power_kw is not None and mode is not CalculationMode.POWER_CONSTRAINED:
        if metrics.power_kw > available_power_kw:
            feasibility_warning = translate(
                locale,
                "warning.feasibility",
                required_kw=metrics.power_kw,
                available_kw=available_power_kw,
            )

    if unit_system is UnitSystem.IMPERIAL:
        feed_rate = mm_to_in(metrics.feed_rate_mm_min)
        torque = nm_to_in_lb(metrics.torque_nm)
        power_required = kw_to_hp(metrics.power_kw)
    else:
        feed_rate = metrics.feed_rate_mm_min
        torque = metrics.torque_nm
        power_required = metrics.power_kw

    return CalculationResult(
        spindle_speed_rpm=metrics.spindle_speed_rpm,
        feed_rate=feed_rate,
        machining_time=metrics.machining_time_min,
        torque=torque,
        power_required=power_required,
        unit_system=unit_system,
        feasibility_warning=feasibility_warning,
        error=None,
        mode=mode,
    )


def calculate(
    diameter: float,
    depth: float,
    material: str,
    tool: str,
    unit_system: UnitSystem = UnitSystem.METRIC,
    available_power: float | None = None,
    config_path: str | None = None,
    locale: str = DEFAULT_LOCALE,
    mode: CalculationMode = CalculationMode.STANDARD,
    target_rpm: float | None = None,
    materials_config_path: str | None = None,
) -> CalculationResult:
    """Calculate drilling parameters for the given inputs.

    Never raises for expected validation failures (invalid input,
    missing/unknown material or tool, unsupported combination, exceeded
    power rating) — always returns a :class:`CalculationResult` instead
    (FR-015). See ``contracts/library-api.md`` and
    ``specs/002-constrained-calculation-modes/contracts/library-api-delta.md``
    for the full contract and error codes.

    Args:
        diameter: Drill diameter, in the units of ``unit_system`` (mm for
            METRIC, inches for IMPERIAL).
        depth: Hole depth, in the units of ``unit_system``.
        material: A workpiece material name from :func:`list_materials`.
        tool: A drilling tool name from :func:`list_tools`.
        unit_system: The unit system for both input parsing and output
            formatting (FR-017). Defaults to ``UnitSystem.METRIC``.
        available_power: Optional available machine power, in the power
            unit of ``unit_system`` (kW for METRIC, HP for IMPERIAL).
            Semantics depend on ``mode``: in ``STANDARD`` and
            ``FIXED_RPM`` modes it is optional/advisory — an exceeded
            budget sets a ``feasibility_warning`` (FR-012 of the base
            spec, FR-008 of this feature) without altering the result. In
            ``POWER_CONSTRAINED`` mode it is a **required** hard
            constraint (FR-002).
        config_path: Optional path to a TOML file overriding the default
            diameter/depth validation bounds (FR-018).
        locale: Optional locale used to translate ``ErrorInfo.message`` and
            ``feasibility_warning`` text (FR-019d). Defaults to English; an
            empty string is treated the same as omitting it. Falls back to
            English for any locale or message key not present in the
            requested catalog (FR-019e).
        mode: Which calculation mode to use (``STANDARD``,
            ``POWER_CONSTRAINED``, or ``FIXED_RPM``). Defaults to
            ``STANDARD``, which is byte-for-byte identical to
            ``001-metal-drilling-calc``'s behavior (SC-004).
        target_rpm: Required when ``mode is CalculationMode.FIXED_RPM``:
            the caller-supplied spindle speed (RPM) to calculate from,
            instead of deriving it from the material/tool. Ignored (not an
            error) when ``mode is CalculationMode.STANDARD``. Supplying it
            together with ``mode is CalculationMode.POWER_CONSTRAINED`` is
            a ``MODE_CONFLICT`` (FR-009).
        materials_config_path: Optional path to a user-supplied
            materials/tools configuration file
            (``contracts/materials-config-schema.md``) that adds new
            materials/tools or overrides built-in ones (FR-002 of
            005-configurable-materials-tools). Unrelated to ``config_path``
            above, which continues to mean only the validation-bounds file
            (FR-017). Defaults to ``None`` (bundled defaults only,
            byte-for-byte identical to pre-feature behavior, FR-014). May
            raise :class:`mfgparams.registry_config.RegistryConfigError`
            if the supplied file exists but is malformed or contains a
            duplicate/invalid entry; a missing/unreadable file is not an
            error (FR-005) and behaves like ``None``.

    Returns:
        A :class:`CalculationResult`. On success, ``error`` is ``None`` and:

        - ``spindle_speed_rpm`` is in RPM (identical under both unit
          systems).
        - ``feed_rate`` is in mm/min (METRIC) or in/min (IMPERIAL).
        - ``machining_time`` is in minutes (fractional), identical under
          both unit systems.
        - ``torque`` is in N*m (METRIC) or in-lb (IMPERIAL).
        - ``power_required`` is in kW (METRIC) or HP (IMPERIAL).
        - ``mode`` echoes the requested mode (FR-012).

        On failure, ``error`` is set (one of the base spec's five codes,
        or this feature's ``INVALID_TARGET_RPM``, ``MODE_CONFLICT``, or
        ``INFEASIBLE_POWER_BUDGET``) and all numeric fields above are
        ``None``.
    """

    # An empty string is treated the same as omitting locale (FR-019d).
    locale = locale or DEFAULT_LOCALE

    prepared = _validate_and_prepare(
        diameter,
        depth,
        material,
        tool,
        unit_system,
        available_power,
        config_path,
        locale,
        mode,
        target_rpm,
        materials_config_path,
    )
    if isinstance(prepared, CalculationResult):
        return prepared
    resolved_material, resolved_tool, diameter_mm, depth_mm, available_power_kw = prepared

    metrics_or_error = _compute_metrics(
        mode,
        diameter_mm,
        depth_mm,
        resolved_material,
        resolved_tool,
        available_power_kw,
        target_rpm,
        unit_system,
        locale,
    )
    if isinstance(metrics_or_error, CalculationResult):
        return metrics_or_error

    return _build_result(metrics_or_error, unit_system, available_power_kw, mode, locale)
