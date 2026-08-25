"""Drilling calculation formulas (FR-006, FR-007, FR-008, FR-011).

Standard twist-drill machining formulas as published in widely-referenced
industry sources (Sandvik Coromant's "Machining Formulas" reference and
Machinery's Handbook); see ``specs/001-metal-drilling-calc/research.md`` #4
for the full citation and rationale. All inputs/outputs here are canonical
metric; imperial conversion happens at the operation-orchestration layer
(``operations/drilling/__init__.py``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mfgparams.registry import WorkpieceMaterial

from .tools import DrillingTool

# Point-engagement allowance for a standard 118-degree drill point,
# approximated as a fraction of drill diameter (research.md #4).
POINT_ANGLE_ALLOWANCE_FACTOR = 0.3


@dataclass(frozen=True)
class DrillingMetrics:
    """Canonical-metric drilling calculation outputs.

    Attributes:
        spindle_speed_rpm: Spindle speed, in RPM.
        feed_rate_mm_min: Feed rate, in mm/min.
        machining_time_min: Machining time, in minutes (fractional).
        torque_nm: Cutting torque, in N*m.
        power_kw: Cutting power required, in kW.
    """

    spindle_speed_rpm: float
    feed_rate_mm_min: float
    machining_time_min: float
    torque_nm: float
    power_kw: float


def calculate_drilling_metrics_at_rpm(
    diameter_mm: float,
    depth_mm: float,
    material: WorkpieceMaterial,
    tool: DrillingTool,
    spindle_speed_rpm: float,
) -> DrillingMetrics:
    """Compute drilling parameters for an explicit spindle speed.

    Shared by all three calculation modes (research.md #2 of
    ``002-constrained-calculation-modes``): the standard mode derives its
    nominal spindle speed from cutting speed and delegates here; the
    power-constrained mode passes its algebraically adjusted spindle speed
    (research.md #1); the fixed-RPM mode passes the caller-supplied
    ``target_rpm`` directly (FR-006).

    Args:
        diameter_mm: Drill diameter, in mm (must already be validated > 0).
        depth_mm: Hole depth, in mm (must already be validated > 0).
        material: The resolved workpiece material reference data.
        tool: The resolved drilling tool reference data.
        spindle_speed_rpm: Spindle speed to calculate at, in RPM (must be
            a positive, finite number; not validated here).

    Returns:
        The computed :class:`DrillingMetrics`.
    """

    feed_per_rev_mm = material.reference_feed_per_rev_mm * tool.feed_factor

    # Feed rate: vf = n * fn
    feed_rate_mm_min = spindle_speed_rpm * feed_per_rev_mm

    # Machining time: tc = (depth + point-engagement allowance) / vf
    point_allowance_mm = POINT_ANGLE_ALLOWANCE_FACTOR * diameter_mm
    machining_time_min = (depth_mm + point_allowance_mm) / feed_rate_mm_min

    # Torque: Mc = (Kc * D^2 * fn) / 4000 — independent of spindle speed
    # (research.md #1).
    torque_nm = (material.specific_cutting_force_kc * diameter_mm**2 * feed_per_rev_mm) / 4000

    # Power: Pc = (Mc * n) / 9550
    power_kw = (torque_nm * spindle_speed_rpm) / 9550

    return DrillingMetrics(
        spindle_speed_rpm=spindle_speed_rpm,
        feed_rate_mm_min=feed_rate_mm_min,
        machining_time_min=machining_time_min,
        torque_nm=torque_nm,
        power_kw=power_kw,
    )


def calculate_drilling_metrics(
    diameter_mm: float,
    depth_mm: float,
    material: WorkpieceMaterial,
    tool: DrillingTool,
) -> DrillingMetrics:
    """Compute drilling parameters for validated, canonical-metric inputs.

    Args:
        diameter_mm: Drill diameter, in mm (must already be validated > 0).
        depth_mm: Hole depth, in mm (must already be validated > 0).
        material: The resolved workpiece material reference data.
        tool: The resolved drilling tool reference data.

    Returns:
        The computed :class:`DrillingMetrics`.
    """

    # Effective cutting speed (vc): the tool's factor multiplies the
    # material's HSS-baseline reference value (FR-006, FR-007;
    # data-model.md DrillingTool).
    cutting_speed_m_min = material.reference_cutting_speed_m_min * tool.cutting_speed_factor

    # Spindle speed: n = (vc * 1000) / (pi * D)
    spindle_speed_rpm = (cutting_speed_m_min * 1000) / (math.pi * diameter_mm)

    return calculate_drilling_metrics_at_rpm(
        diameter_mm, depth_mm, material, tool, spindle_speed_rpm
    )


def calculate_power_constrained_metrics(
    diameter_mm: float,
    depth_mm: float,
    material: WorkpieceMaterial,
    tool: DrillingTool,
    available_power_kw: float,
) -> DrillingMetrics:
    """Compute drilling parameters adjusted to fit an available power budget.

    Implements the closed-form (non-iterative) power-scaling derivation
    (research.md #1 of ``002-constrained-calculation-modes``): since torque
    is independent of spindle speed, required power scales linearly with
    spindle speed for a fixed diameter/material/tool selection, so the
    highest spindle speed that keeps required power within budget can be
    solved algebraically in a single step.

    Args:
        diameter_mm: Drill diameter, in mm (must already be validated > 0).
        depth_mm: Hole depth, in mm (must already be validated > 0).
        material: The resolved workpiece material reference data.
        tool: The resolved drilling tool reference data.
        available_power_kw: The available power budget, in kW. Must be a
            positive number (not validated here — callers reject
            non-positive budgets under ``INFEASIBLE_POWER_BUDGET``, FR-004,
            before calling this function).

    Returns:
        The computed :class:`DrillingMetrics` at the nominal spindle speed
        (FR-003, if ``available_power_kw`` is already sufficient — within
        ``math.isclose()``'s default ``rel_tol=1e-9`` — including the exact
        equality boundary), or at the algebraically reduced spindle speed
        (FR-002, otherwise).
    """

    nominal = calculate_drilling_metrics(diameter_mm, depth_mm, material, tool)

    if nominal.power_kw <= available_power_kw or math.isclose(
        nominal.power_kw, available_power_kw, rel_tol=1e-9
    ):
        # Already sufficient, including the exact-equality boundary — no
        # reduction is applied (FR-003, spec.md Clarifications 2026-07-11).
        return nominal

    # n_adjusted = n0 * (Pavail / Pc0) — power scales linearly with
    # spindle speed since torque does not depend on it (research.md #1).
    n_adjusted = nominal.spindle_speed_rpm * (available_power_kw / nominal.power_kw)

    return calculate_drilling_metrics_at_rpm(diameter_mm, depth_mm, material, tool, n_adjusted)
