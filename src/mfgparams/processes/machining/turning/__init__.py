"""Turning operation: public entry point (specs/019-turning-calculations
FR-001 through FR-017).

Re-exported at the top level as ``mfgparams.calculate_turning``, alongside
the existing drilling ``calculate()`` and milling ``calculate_end_milling``/
``calculate_face_milling`` (all unchanged). Turning is a single-subtype
process like drilling, so this module mirrors
``processes/machining/drilling/__init__.py``'s shape directly rather than
sharing milling's multi-sub-operation ``_calculate.py`` engine (data-model.md
"Structure Decision"; Constitution Principle VI).
"""

from __future__ import annotations

import math

from mfgparams.config import load_configuration
from mfgparams.i18n import DEFAULT_LOCALE, translate
from mfgparams.models import CalculationMode, CalculationResult, ErrorInfo, UnitSystem
from mfgparams.registry import get_material, get_material_validation
from mfgparams.units import (
    kw_to_hp,
    mm_to_in,
    n_to_lbf,
    nm_to_in_lb,
    to_metric_length,
    to_metric_power,
)
from mfgparams.validation import (
    validate_material_present,
    validate_mode_arguments,
    validate_target_rpm,
    validate_turning_depth_of_cut_mm,
    validate_turning_diameter_mm,
    validate_turning_length_of_cut_mm,
    validate_turning_tool_present,
)

from .formulas import (
    calculate_turning_metrics,
    calculate_turning_metrics_at_rpm,
    calculate_turning_power_constrained_metrics,
)
from .tools import get_turning_tool, list_turning_tools


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
        cutting_force=None,
    )


def _reject_if_invalid(
    metrics,
    unit_system: UnitSystem,
    mode: CalculationMode,
    locale: str,
    *,
    error_code: str,
    error_message_key: str,
):
    """Guard against a metrics result with any non-finite or non-positive field.

    Mirrors milling's ``_calculate._reject_if_invalid`` exactly (Copilot
    review finding on PR #100: an extreme-but-individually-"valid" input —
    e.g. a subnormal diameter, or a ``target_rpm``/power budget that scales
    spindle speed down towards zero — can make a field underflow to
    exactly ``0.0`` or overflow to ``inf``/``nan`` while other fields stay
    finite, silently returning a meaningless "successful" result with
    ``error is None``). Every field here is a product/quotient of strictly
    positive validated inputs, so none of them can ever legitimately be
    zero or non-finite; reaching one is always underflow/overflow, never a
    real result, and must not violate the never-raises, structured-error
    API contract.
    """

    if all(
        math.isfinite(value) and value > 0
        for value in (
            metrics.spindle_speed_rpm,
            metrics.feed_rate_mm_min,
            metrics.machining_time_min,
            metrics.cutting_force_n,
            metrics.torque_nm,
            metrics.power_kw,
        )
    ):
        return metrics
    return _error_result(
        unit_system,
        ErrorInfo(error_code, translate(locale, error_message_key), message_key=error_message_key),
        mode,
    )


def _compute_metrics(
    mode: CalculationMode,
    diameter_mm: float,
    depth_of_cut_mm: float,
    length_of_cut_mm: float,
    resolved_material,
    resolved_tool,
    available_power_kw: float | None,
    target_rpm: float | None,
    unit_system: UnitSystem,
    locale: str,
):
    """Dispatch to the mode-specific metrics calculation.

    Mirrors drilling's ``_compute_metrics`` shape (three modes, same
    dispatch structure), extended to turning's three-dimensional geometry
    (diameter, depth of cut, length of cut) and to milling's
    ``_reject_if_invalid`` finiteness/positivity guard, applied to every
    mode's result rather than only checking ``spindle_speed_rpm`` in
    ``POWER_CONSTRAINED`` mode (Copilot review finding on PR #100).
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
                    message_key="error.infeasible_power_budget",
                ),
                mode,
            )
        metrics = calculate_turning_power_constrained_metrics(
            diameter_mm,
            depth_of_cut_mm,
            length_of_cut_mm,
            resolved_material,
            resolved_tool,
            available_power_kw,
        )
        return _reject_if_invalid(
            metrics,
            unit_system,
            mode,
            locale,
            error_code="INFEASIBLE_POWER_BUDGET",
            error_message_key="error.infeasible_power_budget",
        )

    if mode is CalculationMode.FIXED_RPM:
        # target_rpm is guaranteed non-None here (INVALID_TARGET_RPM is
        # returned earlier in calculate_turning() when it is None for this
        # mode).
        assert target_rpm is not None
        metrics = calculate_turning_metrics_at_rpm(
            diameter_mm,
            depth_of_cut_mm,
            length_of_cut_mm,
            resolved_material,
            resolved_tool,
            target_rpm,
        )
        return _reject_if_invalid(
            metrics,
            unit_system,
            mode,
            locale,
            error_code="CALCULATION_OVERFLOW",
            error_message_key="error.calculation_overflow",
        )

    standard_metrics = calculate_turning_metrics(
        diameter_mm, depth_of_cut_mm, length_of_cut_mm, resolved_material, resolved_tool
    )
    return _reject_if_invalid(
        standard_metrics,
        unit_system,
        mode,
        locale,
        error_code="CALCULATION_OVERFLOW",
        error_message_key="error.calculation_overflow",
    )


def _resolve_material_and_tool(
    material: str,
    tool: str,
    unit_system: UnitSystem,
    locale: str,
    mode: CalculationMode,
    materials_config_path: str | None = None,
):
    """Validate and resolve the material/tool names to their registry entries.

    Mirrors drilling's ``_resolve_material_and_tool``, using turning's own
    ``validate_turning_tool_present``/``get_turning_tool`` (a *drilling*
    tool's message wording would be wrong here).
    """
    material_error = validate_material_present(material, locale)
    if material_error:
        return _error_result(unit_system, material_error, mode)

    tool_error = validate_turning_tool_present(tool, locale)
    if tool_error:
        return _error_result(unit_system, tool_error, mode)

    resolved_material = get_material(material, materials_config_path)
    if resolved_material is None:
        return _error_result(
            unit_system,
            ErrorInfo(
                "MISSING_MATERIAL",
                translate(locale, "error.unknown_material", material=material),
                message_key="error.unknown_material",
                kwargs=(("material", material),),
            ),
            mode,
        )
    if not resolved_material.is_usable:
        validation = get_material_validation(material, materials_config_path)
        details = "; ".join(validation.issues) if validation is not None else ""
        return _error_result(
            unit_system,
            ErrorInfo(
                "UNUSABLE_MATERIAL",
                translate(locale, "error.unusable_material", material=material, details=details),
                message_key="error.unusable_material",
                kwargs=(("material", material), ("details", details)),
            ),
            mode,
        )

    resolved_tool = get_turning_tool(tool, materials_config_path)
    if resolved_tool is None:
        return _error_result(
            unit_system,
            ErrorInfo(
                "MISSING_TOOL",
                translate(locale, "error.unknown_turning_tool", tool=tool),
                message_key="error.unknown_turning_tool",
                kwargs=(("tool", tool),),
            ),
            mode,
        )

    return resolved_material, resolved_tool


def _validate_geometry(
    diameter: float,
    depth_of_cut: float,
    length_of_cut: float,
    unit_system: UnitSystem,
    config,
    locale: str,
    mode: CalculationMode,
):
    """Convert diameter/depth of cut/length of cut to metric and validate them.

    Returns a :class:`CalculationResult` if invalid, or the tuple
    ``(diameter_mm, depth_of_cut_mm, length_of_cut_mm)`` on success. Mirrors
    drilling's ``_validate_geometry``, extended to turning's third
    dimensional input.
    """
    diameter_mm = to_metric_length(diameter, unit_system)
    depth_of_cut_mm = to_metric_length(depth_of_cut, unit_system)
    length_of_cut_mm = to_metric_length(length_of_cut, unit_system)

    diameter_error = validate_turning_diameter_mm(diameter_mm, config, locale)
    if diameter_error:
        return _error_result(unit_system, diameter_error, mode)

    depth_of_cut_error = validate_turning_depth_of_cut_mm(
        depth_of_cut_mm, diameter_mm, config, locale
    )
    if depth_of_cut_error:
        return _error_result(unit_system, depth_of_cut_error, mode)

    length_of_cut_error = validate_turning_length_of_cut_mm(length_of_cut_mm, config, locale)
    if length_of_cut_error:
        return _error_result(unit_system, length_of_cut_error, mode)

    return diameter_mm, depth_of_cut_mm, length_of_cut_mm


def _validate_mode_inputs(
    mode: CalculationMode,
    available_power: float | None,
    target_rpm: float | None,
    unit_system: UnitSystem,
    locale: str,
):
    """Validate the mode-specific arguments (``target_rpm``/``available_power``).

    Byte-for-byte the same as drilling's ``_validate_mode_inputs`` — mode
    validation is operation-agnostic, so it is reused verbatim rather than
    duplicated.
    """
    if mode is CalculationMode.FIXED_RPM:
        target_rpm_error = validate_target_rpm(target_rpm, locale)
        if target_rpm_error:
            return _error_result(unit_system, target_rpm_error, mode)
        if target_rpm is None:
            return _error_result(
                unit_system,
                ErrorInfo(
                    "INVALID_TARGET_RPM",
                    translate(locale, "error.invalid_target_rpm"),
                    message_key="error.invalid_target_rpm",
                ),
                mode,
            )

    return (
        _error_result(unit_system, mode_error, mode)
        if (mode_error := validate_mode_arguments(mode, available_power, target_rpm, locale))
        else None
    )


def _validate_and_prepare(
    diameter: float,
    depth_of_cut: float,
    length_of_cut: float,
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

    Mirrors drilling's ``_validate_and_prepare``, extended to turning's
    three-dimensional geometry.
    """
    config = load_configuration(config_path)

    resolved = _resolve_material_and_tool(
        material, tool, unit_system, locale, mode, materials_config_path
    )
    if isinstance(resolved, CalculationResult):
        return resolved
    resolved_material, resolved_tool = resolved

    geometry = _validate_geometry(
        diameter, depth_of_cut, length_of_cut, unit_system, config, locale, mode
    )
    if isinstance(geometry, CalculationResult):
        return geometry
    diameter_mm, depth_of_cut_mm, length_of_cut_mm = geometry

    mode_input_error = _validate_mode_inputs(mode, available_power, target_rpm, unit_system, locale)
    if mode_input_error is not None:
        return mode_input_error

    available_power_kw = None
    if available_power is not None:
        available_power_kw = to_metric_power(available_power, unit_system)

    return (
        resolved_material,
        resolved_tool,
        diameter_mm,
        depth_of_cut_mm,
        length_of_cut_mm,
        available_power_kw,
    )


def _build_result(
    metrics,
    unit_system: UnitSystem,
    available_power_kw: float | None,
    mode: CalculationMode,
    locale: str,
) -> CalculationResult:
    """Apply unit conversion, the feasibility-warning check, and build the
    final success :class:`CalculationResult`. Mirrors drilling's
    ``_build_result``, extended with the new ``cutting_force`` field."""
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
        cutting_force = n_to_lbf(metrics.cutting_force_n)
    else:
        feed_rate = metrics.feed_rate_mm_min
        torque = metrics.torque_nm
        power_required = metrics.power_kw
        cutting_force = metrics.cutting_force_n

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
        cutting_force=cutting_force,
    )


def calculate_turning(
    diameter: float,
    depth_of_cut: float,
    length_of_cut: float,
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
    """Calculate turning parameters for the given inputs.

    Never raises for expected validation failures (invalid input,
    missing/unknown material or tool, unsupported combination, depth of cut
    not less than the workpiece radius, mode-argument conflicts, infeasible
    power budget, exceeded power rating) — always returns a
    :class:`CalculationResult` instead. See
    ``specs/019-turning-calculations/contracts/library-api-turning.md`` for
    the full contract and error codes.

    Args:
        diameter: Workpiece diameter, in the units of ``unit_system`` (mm
            for METRIC, inches for IMPERIAL).
        depth_of_cut: Radial depth of cut per pass (ap), in the units of
            ``unit_system``. Must be less than half the workpiece diameter.
        length_of_cut: Length of the turning pass (lm), in the units of
            ``unit_system``.
        material: A workpiece material name from :func:`list_materials`.
        tool: A turning tool name from :func:`list_turning_tools`.
        unit_system: The unit system for both input parsing and output
            formatting. Defaults to ``UnitSystem.METRIC``.
        available_power: Optional available lathe/tool power, in the power
            unit of ``unit_system`` (kW for METRIC, HP for IMPERIAL).
            Semantics depend on ``mode``: in ``STANDARD`` and ``FIXED_RPM``
            modes it is optional/advisory; in ``POWER_CONSTRAINED`` mode it
            is a **required** hard constraint.
        config_path: Optional path to a TOML file overriding the default
            diameter/depth-of-cut/length-of-cut validation bounds.
        locale: Optional locale used to translate ``feasibility_warning``
            text. Defaults to English. Does not affect ``ErrorInfo.message``,
            which is always English regardless of this argument.
        mode: Which calculation mode to use (``STANDARD``,
            ``POWER_CONSTRAINED``, or ``FIXED_RPM``). Defaults to
            ``STANDARD``.
        target_rpm: Required when ``mode is CalculationMode.FIXED_RPM``:
            the caller-supplied spindle speed (RPM) to calculate from,
            instead of deriving it from the material/tool. Ignored (not an
            error) when ``mode is CalculationMode.STANDARD``. Supplying it
            together with ``mode is CalculationMode.POWER_CONSTRAINED`` is
            a ``MODE_CONFLICT``.
        materials_config_path: Optional path to a user-supplied
            materials/tools configuration file that adds new materials/
            tools or overrides built-in ones. Defaults to ``None`` (bundled
            defaults only).

    Returns:
        A :class:`CalculationResult`. On success, ``error`` is ``None`` and:

        - ``spindle_speed_rpm`` is in RPM (identical under both unit
          systems).
        - ``feed_rate`` is in mm/min (METRIC) or in/min (IMPERIAL).
        - ``machining_time`` is in minutes (fractional), identical under
          both unit systems.
        - ``torque`` is in N*m (METRIC) or in-lb (IMPERIAL).
        - ``power_required`` is in kW (METRIC) or HP (IMPERIAL).
        - ``cutting_force`` is in newtons (METRIC) or lbf (IMPERIAL).
        - ``mode`` echoes the requested mode.

        On failure, ``error`` is set and every numeric field above,
        including ``cutting_force``, is ``None``.
    """

    locale = locale or DEFAULT_LOCALE
    message_locale = DEFAULT_LOCALE

    prepared = _validate_and_prepare(
        diameter,
        depth_of_cut,
        length_of_cut,
        material,
        tool,
        unit_system,
        available_power,
        config_path,
        message_locale,
        mode,
        target_rpm,
        materials_config_path,
    )
    if isinstance(prepared, CalculationResult):
        return prepared
    (
        resolved_material,
        resolved_tool,
        diameter_mm,
        depth_of_cut_mm,
        length_of_cut_mm,
        available_power_kw,
    ) = prepared

    metrics_or_error = _compute_metrics(
        mode,
        diameter_mm,
        depth_of_cut_mm,
        length_of_cut_mm,
        resolved_material,
        resolved_tool,
        available_power_kw,
        target_rpm,
        unit_system,
        message_locale,
    )
    if isinstance(metrics_or_error, CalculationResult):
        return metrics_or_error

    return _build_result(metrics_or_error, unit_system, available_power_kw, mode, locale)


__all__ = [
    "calculate_turning",
    "get_turning_tool",
    "list_turning_tools",
]
