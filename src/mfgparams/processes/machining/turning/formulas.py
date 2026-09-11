"""Turning calculation formulas (specs/019-turning-calculations FR-006 through FR-009).

Standard single-point turning formulas as published in widely-referenced
industry sources (Sandvik Coromant's "Machining Formulas" reference and
Machinery's Handbook — the same class of source already cited in
``specs/001-metal-drilling-calc/research.md`` #4 for drilling's own
formulas); see ``specs/019-turning-calculations/research.md`` #1 for the
full citation and rationale. All inputs/outputs here are canonical metric;
imperial conversion happens at the operation-orchestration layer
(``processes/machining/turning/__init__.py``).

Unlike drilling, turning's machining-time formula has no point-engagement
allowance term: a single-point turning tool has no drill-point geometry to
account for (research.md #2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mfgparams.registry import WorkpieceMaterial

from .tools import TurningTool


@dataclass(frozen=True)
class TurningMetrics:
    """Canonical-metric turning calculation outputs.

    Attributes:
        spindle_speed_rpm: Spindle speed, in RPM.
        feed_rate_mm_min: Feed rate, in mm/min.
        machining_time_min: Machining time, in minutes (fractional).
        cutting_force_n: Tangential cutting force (Fc), in newtons.
        torque_nm: Spindle torque implied by the cutting force acting at
            the workpiece radius, in N*m.
        power_kw: Cutting power required, in kW.
    """

    spindle_speed_rpm: float
    feed_rate_mm_min: float
    machining_time_min: float
    cutting_force_n: float
    torque_nm: float
    power_kw: float


def calculate_turning_metrics_at_rpm(
    diameter_mm: float,
    depth_of_cut_mm: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    tool: TurningTool,
    spindle_speed_rpm: float,
) -> TurningMetrics:
    """Compute turning parameters for an explicit spindle speed.

    Shared by all three calculation modes, mirroring drilling's
    ``calculate_drilling_metrics_at_rpm`` exactly: the standard mode derives
    its nominal spindle speed from cutting speed and delegates here; the
    power-constrained mode passes its algebraically adjusted spindle speed
    (research.md #1); the fixed-RPM mode passes the caller-supplied
    ``target_rpm`` directly.

    Args:
        diameter_mm: Workpiece diameter, in mm (must already be validated > 0).
        depth_of_cut_mm: Radial depth of cut per pass (ap), in mm (must
            already be validated > 0 and < diameter_mm / 2).
        length_of_cut_mm: Length of the turning pass (lm), in mm (must
            already be validated > 0).
        material: The resolved workpiece material reference data.
        tool: The resolved turning tool reference data.
        spindle_speed_rpm: Spindle speed to calculate at, in RPM (must be
            a positive, finite number; not validated here).

    Returns:
        The computed :class:`TurningMetrics`.
    """

    # An arbitrary-precision Python int too large to convert to a C double
    # (e.g. target_rpm=10**1000 in FIXED_RPM mode -- validate_target_rpm's
    # finiteness check accepts it, since Python ints are always "finite")
    # would otherwise raise OverflowError from the very first
    # multiplication below. inf is the mathematically sensible limit for
    # an unrepresentably large spindle speed, and is caught by the
    # orchestration layer's finiteness check afterwards (Copilot review
    # finding on PR #100).
    try:
        spindle_speed_rpm = float(spindle_speed_rpm)
    except OverflowError:
        spindle_speed_rpm = math.inf

    feed_per_rev_mm = material.reference_feed_per_rev_mm * tool.feed_factor

    # Feed rate: vf = n * fn
    feed_rate_mm_min = spindle_speed_rpm * feed_per_rev_mm

    # Machining time: Tc = lm / vf (no point-engagement allowance -- research.md #2)
    # A subnormal-but-finite spindle_speed_rpm/feed_per_rev_mm can make
    # feed_rate_mm_min underflow to exactly 0.0 (e.g. target_rpm=5e-324 in
    # FIXED_RPM mode, which has no lower bound beyond positivity/
    # finiteness -- Copilot review finding on PR #100). Python raises
    # ZeroDivisionError for float/0.0 rather than returning inf, so guard
    # explicitly, mirroring milling's identical guard
    # (processes/machining/milling/_shared.py). inf is the mathematically
    # correct machining time at a zero feed rate, and is caught by the
    # orchestration layer's finiteness check (__init__.py).
    machining_time_min = (
        float("inf") if feed_rate_mm_min == 0 else length_of_cut_mm / feed_rate_mm_min
    )

    # Cutting force: Fc = Kc * ap * fn -- independent of spindle speed
    # (research.md #1), the direct turning analogue of drilling's torque
    # formula.
    cutting_force_n = material.specific_cutting_force_kc * depth_of_cut_mm * feed_per_rev_mm

    # Torque: Mc = Fc * (D / 2) / 1000 -- the spindle torque implied by the
    # cutting force acting at the workpiece radius (mm -> m conversion via
    # /1000); also independent of spindle speed.
    torque_nm = cutting_force_n * (diameter_mm / 2) / 1000

    # Power: Pc = (Mc * n) / 9550 -- byte-for-byte the same formula
    # drilling's power uses, since it only depends on torque and RPM being
    # in the stated units, not on how torque was derived.
    power_kw = (torque_nm * spindle_speed_rpm) / 9550

    return TurningMetrics(
        spindle_speed_rpm=spindle_speed_rpm,
        feed_rate_mm_min=feed_rate_mm_min,
        machining_time_min=machining_time_min,
        cutting_force_n=cutting_force_n,
        torque_nm=torque_nm,
        power_kw=power_kw,
    )


def calculate_turning_metrics(
    diameter_mm: float,
    depth_of_cut_mm: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    tool: TurningTool,
) -> TurningMetrics:
    """Compute turning parameters for validated, canonical-metric inputs (standard mode).

    Args:
        diameter_mm: Workpiece diameter, in mm (must already be validated > 0).
        depth_of_cut_mm: Radial depth of cut per pass (ap), in mm.
        length_of_cut_mm: Length of the turning pass (lm), in mm.
        material: The resolved workpiece material reference data.
        tool: The resolved turning tool reference data.

    Returns:
        The computed :class:`TurningMetrics`.
    """

    # Effective cutting speed (vc): the tool's factor multiplies the
    # material's HSS-baseline reference value, exactly as drilling's does.
    cutting_speed_m_min = material.reference_cutting_speed_m_min * tool.cutting_speed_factor

    # Spindle speed: n = (vc * 1000) / (pi * D)
    spindle_speed_rpm = (cutting_speed_m_min * 1000) / (math.pi * diameter_mm)

    return calculate_turning_metrics_at_rpm(
        diameter_mm, depth_of_cut_mm, length_of_cut_mm, material, tool, spindle_speed_rpm
    )


def calculate_turning_power_constrained_metrics(
    diameter_mm: float,
    depth_of_cut_mm: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    tool: TurningTool,
    available_power_kw: float,
) -> TurningMetrics:
    """Compute turning parameters adjusted to fit an available power budget.

    Implements the same closed-form (non-iterative) power-scaling
    derivation drilling's ``calculate_power_constrained_metrics`` uses
    (research.md #1): since torque (and cutting force) are independent of
    spindle speed, required power scales linearly with spindle speed for a
    fixed diameter/depth-of-cut/material/tool selection, so the highest
    spindle speed that keeps required power within budget can be solved
    algebraically in a single step.

    Args:
        diameter_mm: Workpiece diameter, in mm (must already be validated > 0).
        depth_of_cut_mm: Radial depth of cut per pass (ap), in mm.
        length_of_cut_mm: Length of the turning pass (lm), in mm.
        material: The resolved workpiece material reference data.
        tool: The resolved turning tool reference data.
        available_power_kw: The available power budget, in kW. Must be a
            positive number (not validated here — callers reject
            non-positive budgets under ``INFEASIBLE_POWER_BUDGET`` before
            calling this function).

    Returns:
        The computed :class:`TurningMetrics` at the nominal spindle speed
        if ``available_power_kw`` is already sufficient (including the
        exact equality boundary, via ``math.isclose()``'s default
        ``rel_tol=1e-9``), or at the algebraically reduced spindle speed
        otherwise.
    """

    nominal = calculate_turning_metrics(
        diameter_mm, depth_of_cut_mm, length_of_cut_mm, material, tool
    )

    if nominal.power_kw <= available_power_kw or math.isclose(
        nominal.power_kw, available_power_kw, rel_tol=1e-9
    ):
        return nominal

    # n_adjusted = n0 * (Pavail / Pc0) -- power scales linearly with
    # spindle speed since torque/cutting force do not depend on it
    # (research.md #1).
    n_adjusted = nominal.spindle_speed_rpm * (available_power_kw / nominal.power_kw)

    return calculate_turning_metrics_at_rpm(
        diameter_mm, depth_of_cut_mm, length_of_cut_mm, material, tool, n_adjusted
    )
