"""End-milling formulas (specs/009-milling-calculations FR-005).

A thin wrapper over the shared milling formula core
(:func:`mfgparams.operations.milling._shared.calculate_milling_metrics`),
which implements the standard Sandvik Coromant "Machining Formulas"
expressions cited in ``specs/009-milling-calculations/research.md`` #1.

End milling supplies the shared core's radial engagement (``ae``) from the
**radial depth of cut**. Keeping this wrapper — rather than calling the
shared core directly from the entry point — preserves the per-sub-operation
module boundary (FR-014, research.md #2) so a future end-milling-specific
refinement changes only this file.

All inputs/outputs are canonical metric; imperial conversion happens at the
orchestration layer (``end_milling/__init__.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

from mfgparams.operations.milling._shared import (
    calculate_milling_metrics,
    calculate_milling_metrics_at_rpm,
)
from mfgparams.registry import WorkpieceMaterial

from .tools import EndMillTool


@dataclass(frozen=True)
class EndMillingMetrics:
    """Canonical-metric end-milling calculation outputs.

    Attributes:
        spindle_speed_rpm: Spindle speed (n), in RPM.
        feed_rate_mm_min: Table feed rate (vf), in mm/min.
        material_removal_rate_cm3_min: Material removal rate (Q), in
            cm^3/min.
        machining_time_min: Machining time (tc), in minutes (fractional).
        torque_nm: Cutting torque (Mc), in N*m.
        power_kw: Net cutting power (Pc), in kW — power at the cutter, with
            no machine drive-efficiency factor applied.
    """

    spindle_speed_rpm: float
    feed_rate_mm_min: float
    material_removal_rate_cm3_min: float
    machining_time_min: float
    torque_nm: float
    power_kw: float


def calculate_end_milling_metrics(
    diameter_mm: float,
    axial_depth_of_cut_mm: float,
    radial_depth_of_cut_mm: float,
    feed_per_tooth_mm: float,
    number_of_teeth: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    tool: EndMillTool,
) -> EndMillingMetrics:
    """Compute end-milling parameters for validated, canonical-metric inputs.

    Args:
        diameter_mm: End-mill diameter (D), in mm (already validated > 0).
        axial_depth_of_cut_mm: Axial depth of cut (ap), in mm.
        radial_depth_of_cut_mm: Radial depth of cut (ae), in mm (already
            validated > 0 and <= ``diameter_mm``).
        feed_per_tooth_mm: Feed per tooth / chip load (fz), in mm/tooth.
        number_of_teeth: Number of flutes/teeth (zn).
        length_of_cut_mm: Travel distance to be machined, in mm.
        material: The resolved workpiece material reference data.
        tool: The resolved end-mill tool reference data.

    Returns:
        The computed :class:`EndMillingMetrics`.
    """

    metrics = calculate_milling_metrics(
        diameter_mm=diameter_mm,
        axial_depth_of_cut_mm=axial_depth_of_cut_mm,
        radial_engagement_mm=radial_depth_of_cut_mm,
        feed_per_tooth_mm=feed_per_tooth_mm,
        number_of_teeth=number_of_teeth,
        length_of_cut_mm=length_of_cut_mm,
        material=material,
        cutting_speed_factor=tool.cutting_speed_factor,
    )
    return EndMillingMetrics(
        spindle_speed_rpm=metrics.spindle_speed_rpm,
        feed_rate_mm_min=metrics.feed_rate_mm_min,
        material_removal_rate_cm3_min=metrics.material_removal_rate_cm3_min,
        machining_time_min=metrics.machining_time_min,
        torque_nm=metrics.torque_nm,
        power_kw=metrics.power_kw,
    )


def calculate_end_milling_metrics_at_rpm(
    diameter_mm: float,
    axial_depth_of_cut_mm: float,
    radial_depth_of_cut_mm: float,
    feed_per_tooth_mm: float,
    number_of_teeth: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    spindle_speed_rpm: float,
) -> EndMillingMetrics:
    """Compute end-milling parameters for an explicit spindle speed.

    Thin wrapper over
    :func:`mfgparams.operations.milling._shared.calculate_milling_metrics_at_rpm`,
    preserving the per-sub-operation module boundary (FR-014 of
    ``specs/010-milling-calculation-modes``) exactly as
    :func:`calculate_end_milling_metrics` does for the standard path. Used
    by power-constrained mode (with an algebraically adjusted spindle
    speed) and fixed-RPM mode (with the caller-supplied ``target_rpm``
    directly).

    Args:
        diameter_mm: End-mill diameter (D), in mm (already validated > 0).
        axial_depth_of_cut_mm: Axial depth of cut (ap), in mm.
        radial_depth_of_cut_mm: Radial depth of cut (ae), in mm (already
            validated > 0 and <= ``diameter_mm``).
        feed_per_tooth_mm: Feed per tooth / chip load (fz), in mm/tooth.
        number_of_teeth: Number of flutes/teeth (zn).
        length_of_cut_mm: Travel distance to be machined, in mm.
        material: The resolved workpiece material reference data.
        spindle_speed_rpm: Spindle speed to calculate at, in RPM.

    Returns:
        The computed :class:`EndMillingMetrics`.
    """

    metrics = calculate_milling_metrics_at_rpm(
        diameter_mm=diameter_mm,
        axial_depth_of_cut_mm=axial_depth_of_cut_mm,
        radial_engagement_mm=radial_depth_of_cut_mm,
        feed_per_tooth_mm=feed_per_tooth_mm,
        number_of_teeth=number_of_teeth,
        length_of_cut_mm=length_of_cut_mm,
        material=material,
        spindle_speed_rpm=spindle_speed_rpm,
    )
    return EndMillingMetrics(
        spindle_speed_rpm=metrics.spindle_speed_rpm,
        feed_rate_mm_min=metrics.feed_rate_mm_min,
        material_removal_rate_cm3_min=metrics.material_removal_rate_cm3_min,
        machining_time_min=metrics.machining_time_min,
        torque_nm=metrics.torque_nm,
        power_kw=metrics.power_kw,
    )
