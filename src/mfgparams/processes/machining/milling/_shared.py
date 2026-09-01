"""Shared milling formula core for both milling sub-operations.

Implements the standard milling formulas published in Sandvik Coromant's
"Machining Formulas" reference — the same source already cited by
``processes/machining/drilling/formulas.py`` (see
``specs/009-milling-calculations/research.md`` #1 for the full citation and
the derivation of each expression):

1. ``vc = reference_cutting_speed_m_min * cutting_speed_factor``
2. ``n  = (vc * 1000) / (pi * D)`` — spindle speed, RPM
3. ``vf = n * fz * zn`` — table feed rate, mm/min
4. ``Q  = (ap * ae * vf) / 1000`` — material removal rate, cm^3/min
5. ``Pc = (ap * ae * vf * kc) / (60 * 10^6)`` — net cutting power, kW
6. ``Mc = (Pc * 9550) / n`` — cutting torque, N*m
7. ``tc = length_of_cut / vf`` — machining time, minutes

``Pc`` is **net power at the cutter**: no machine drive-efficiency factor is
applied, matching the drilling module's existing convention
(``spec.md`` Assumptions).

This module is internal to ``processes.machining.milling`` and is not part of the
public API. End milling and face milling each wrap it in their own named
metrics dataclass (research.md #2) so the two sub-operations stay
independently versionable even though the arithmetic is identical under the
full/symmetric-engagement assumption: average chip thickness equals the
feed per tooth, so neither chip thinning nor entry/exit angle enters the
calculation for either sub-operation.

All inputs and outputs here are canonical metric; imperial conversion
happens at each sub-operation's orchestration layer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mfgparams.registry import WorkpieceMaterial

#: Conversion constant for ``Q``: (mm * mm * mm/min) -> cm^3/min.
MM3_PER_CM3 = 1000.0

#: Conversion constant for ``Pc``: (mm^2 * mm/min * N/mm^2) -> kW.
#: 60 converts per-minute to per-second, 10^6 converts N*mm/s to kW.
POWER_SCALE = 60.0 * 10**6

#: Standard kW <-> N*m/RPM torque constant (``Mc = Pc * 9550 / n``), the
#: same constant drilling already uses for ``Pc = Mc * n / 9550``.
TORQUE_POWER_CONSTANT = 9550.0


@dataclass(frozen=True)
class MillingMetrics:
    """Canonical-metric milling calculation outputs.

    Attributes:
        spindle_speed_rpm: Spindle speed (n), in RPM.
        feed_rate_mm_min: Table feed rate (vf), in mm/min.
        material_removal_rate_cm3_min: Material removal rate (Q), in
            cm^3/min.
        machining_time_min: Machining time (tc), in minutes (fractional).
        torque_nm: Cutting torque (Mc), in N*m.
        power_kw: Net cutting power (Pc), in kW.
    """

    spindle_speed_rpm: float
    feed_rate_mm_min: float
    material_removal_rate_cm3_min: float
    machining_time_min: float
    torque_nm: float
    power_kw: float


def calculate_milling_metrics_at_rpm(
    diameter_mm: float,
    axial_depth_of_cut_mm: float,
    radial_engagement_mm: float,
    feed_per_tooth_mm: float,
    number_of_teeth: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    spindle_speed_rpm: float,
) -> MillingMetrics:
    """Compute milling parameters for an explicit spindle speed.

    Shared by all three calculation modes
    (``specs/010-milling-calculation-modes/research.md`` #1-#2): the
    standard mode derives its nominal spindle speed from cutting speed and
    delegates here (:func:`calculate_milling_metrics`); the
    power-constrained mode passes its algebraically adjusted spindle speed
    (:func:`calculate_power_constrained_milling_metrics`); the fixed-RPM
    mode passes the caller-supplied ``target_rpm`` directly.

    Args:
        diameter_mm: Tool/cutter diameter (D), in mm (already validated > 0).
        axial_depth_of_cut_mm: Axial depth of cut (ap), in mm (validated > 0).
        radial_engagement_mm: Radial engagement (ae), in mm — the radial
            depth of cut for end milling or the width of cut for face
            milling (already validated > 0 and <= ``diameter_mm``).
        feed_per_tooth_mm: Feed per tooth / chip load (fz), in mm/tooth
            (already validated > 0).
        number_of_teeth: Number of flutes/teeth/inserts (zn) (already
            validated as a positive whole number).
        length_of_cut_mm: Travel distance to be machined, in mm (validated
            > 0).
        material: The resolved workpiece material reference data, supplying
            the specific cutting force (kc).
        spindle_speed_rpm: Spindle speed to calculate at, in RPM (must be a
            positive, finite number; not validated here).

    Returns:
        The computed :class:`MillingMetrics`.
    """

    # 3. Table feed rate: vf = n * fz * zn
    feed_rate_mm_min = spindle_speed_rpm * feed_per_tooth_mm * number_of_teeth

    # 4. Material removal rate: Q = (ap * ae * vf) / 1000
    # Divide the (generally modest) engagement product by MM3_PER_CM3
    # before multiplying by the potentially very large vf (fixed-RPM mode
    # has no upper target_rpm bound), so the intermediate stays
    # representable even where ap * ae * vf itself would overflow to inf
    # despite the final quotient being finite.
    material_removal_rate_cm3_min = (axial_depth_of_cut_mm * radial_engagement_mm / MM3_PER_CM3) * (
        feed_rate_mm_min
    )

    # 5. Net cutting power: Pc = (ap * ae * vf * kc) / (60 * 10^6)
    # Same overflow-avoidance ordering as material removal rate above:
    # divide by the large POWER_SCALE constant before multiplying by vf.
    power_kw = (
        (axial_depth_of_cut_mm * radial_engagement_mm * material.specific_cutting_force_kc)
        / POWER_SCALE
        * feed_rate_mm_min
    )

    # 6. Torque: Mc = (Pc * 9550) / n
    torque_nm = power_kw * (TORQUE_POWER_CONSTANT / spindle_speed_rpm)

    # 7. Machining time: tc = length_of_cut / vf
    # A subnormal-but-finite spindle_speed_rpm/feed_per_tooth_mm can make
    # feed_rate_mm_min underflow to exactly 0.0 (e.g. target_rpm=5e-324 in
    # FIXED_RPM mode, which has no upper *or* lower bound beyond
    # positivity/finiteness) — Python raises ZeroDivisionError for
    # float/0.0 rather than returning inf, so guard explicitly. inf is
    # the mathematically correct machining time at a zero feed rate, and
    # is caught by the caller's finiteness check
    # (_calculate._reject_if_invalid()).
    machining_time_min = (
        float("inf") if feed_rate_mm_min == 0 else length_of_cut_mm / feed_rate_mm_min
    )

    return MillingMetrics(
        spindle_speed_rpm=spindle_speed_rpm,
        feed_rate_mm_min=feed_rate_mm_min,
        material_removal_rate_cm3_min=material_removal_rate_cm3_min,
        machining_time_min=machining_time_min,
        torque_nm=torque_nm,
        power_kw=power_kw,
    )


def calculate_milling_metrics(
    diameter_mm: float,
    axial_depth_of_cut_mm: float,
    radial_engagement_mm: float,
    feed_per_tooth_mm: float,
    number_of_teeth: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    cutting_speed_factor: float,
) -> MillingMetrics:
    """Compute milling parameters for validated, canonical-metric inputs.

    Args:
        diameter_mm: Tool/cutter diameter (D), in mm (already validated > 0).
        axial_depth_of_cut_mm: Axial depth of cut (ap), in mm (validated > 0).
        radial_engagement_mm: Radial engagement (ae), in mm — the radial
            depth of cut for end milling or the width of cut for face
            milling (already validated > 0 and <= ``diameter_mm``).
        feed_per_tooth_mm: Feed per tooth / chip load (fz), in mm/tooth
            (already validated > 0).
        number_of_teeth: Number of flutes/teeth/inserts (zn) (already
            validated as a positive whole number).
        length_of_cut_mm: Travel distance to be machined, in mm (validated
            > 0).
        material: The resolved workpiece material reference data, supplying
            the baseline cutting speed and the specific cutting force (kc).
        cutting_speed_factor: The selected milling tool's multiplier applied
            to the material's baseline cutting speed.

    Returns:
        The computed :class:`MillingMetrics`.
    """

    # 1. Effective cutting speed (vc), m/min.
    cutting_speed_m_min = material.reference_cutting_speed_m_min * cutting_speed_factor

    # 2. Spindle speed: n = (vc * 1000) / (pi * D)
    spindle_speed_rpm = (cutting_speed_m_min * 1000) / (math.pi * diameter_mm)

    return calculate_milling_metrics_at_rpm(
        diameter_mm=diameter_mm,
        axial_depth_of_cut_mm=axial_depth_of_cut_mm,
        radial_engagement_mm=radial_engagement_mm,
        feed_per_tooth_mm=feed_per_tooth_mm,
        number_of_teeth=number_of_teeth,
        length_of_cut_mm=length_of_cut_mm,
        material=material,
        spindle_speed_rpm=spindle_speed_rpm,
    )


def calculate_power_constrained_milling_metrics(
    diameter_mm: float,
    axial_depth_of_cut_mm: float,
    radial_engagement_mm: float,
    feed_per_tooth_mm: float,
    number_of_teeth: float,
    length_of_cut_mm: float,
    material: WorkpieceMaterial,
    cutting_speed_factor: float,
    available_power_kw: float,
) -> MillingMetrics:
    """Compute milling parameters adjusted to fit an available power budget.

    Implements the closed-form (non-iterative) power-scaling derivation
    (``specs/010-milling-calculation-modes/research.md`` #1): since torque
    is independent of spindle speed, required power scales linearly with
    spindle speed for a fixed diameter/material/tool/geometry selection, so
    the highest spindle speed that keeps required power within budget can
    be solved algebraically in a single step — the same identity
    ``specs/002-constrained-calculation-modes`` already established for
    drilling.

    Args:
        diameter_mm: Tool/cutter diameter (D), in mm (already validated > 0).
        axial_depth_of_cut_mm: Axial depth of cut (ap), in mm (validated > 0).
        radial_engagement_mm: Radial engagement (ae), in mm.
        feed_per_tooth_mm: Feed per tooth / chip load (fz), in mm/tooth.
        number_of_teeth: Number of flutes/teeth/inserts (zn).
        length_of_cut_mm: Travel distance to be machined, in mm.
        material: The resolved workpiece material reference data.
        cutting_speed_factor: The selected milling tool's multiplier applied
            to the material's baseline cutting speed.
        available_power_kw: The available power budget, in kW. Must be a
            positive number (not validated here — callers reject
            non-positive budgets under ``INFEASIBLE_POWER_BUDGET`` before
            calling this function).

    Returns:
        The computed :class:`MillingMetrics` at the nominal spindle speed
        (if ``available_power_kw`` is already sufficient — within
        ``math.isclose()``'s default ``rel_tol=1e-9``, including the exact
        equality boundary), or at the algebraically reduced spindle speed
        (otherwise).
    """

    nominal = calculate_milling_metrics(
        diameter_mm=diameter_mm,
        axial_depth_of_cut_mm=axial_depth_of_cut_mm,
        radial_engagement_mm=radial_engagement_mm,
        feed_per_tooth_mm=feed_per_tooth_mm,
        number_of_teeth=number_of_teeth,
        length_of_cut_mm=length_of_cut_mm,
        material=material,
        cutting_speed_factor=cutting_speed_factor,
    )

    if nominal.power_kw <= available_power_kw or math.isclose(
        nominal.power_kw, available_power_kw, rel_tol=1e-9
    ):
        # Already sufficient, including the exact-equality boundary — no
        # reduction is applied (research.md #1).
        return nominal

    # n_adjusted = n0 * (Pavail / Pc0) — power scales linearly with spindle
    # speed since torque does not depend on it (research.md #1).
    n_adjusted = nominal.spindle_speed_rpm * (available_power_kw / nominal.power_kw)

    if not math.isfinite(n_adjusted) or n_adjusted <= 0:
        # An extreme (e.g. positive-subnormal) available_power_kw can make
        # this ratio underflow to exactly zero, or a pathological nominal
        # combination could drive it non-finite. Either way,
        # calculate_milling_metrics_at_rpm() would divide by this rpm and
        # raise ZeroDivisionError, so bail out before calling it — the
        # infeasible sentinel below is what the caller
        # (_calculate._compute_metrics()) already checks
        # spindle_speed_rpm for.
        return _infeasible_sentinel()

    metrics = calculate_milling_metrics_at_rpm(
        diameter_mm=diameter_mm,
        axial_depth_of_cut_mm=axial_depth_of_cut_mm,
        radial_engagement_mm=radial_engagement_mm,
        feed_per_tooth_mm=feed_per_tooth_mm,
        number_of_teeth=number_of_teeth,
        length_of_cut_mm=length_of_cut_mm,
        material=material,
        spindle_speed_rpm=n_adjusted,
    )
    if not all(
        math.isfinite(value)
        for value in (
            metrics.feed_rate_mm_min,
            metrics.material_removal_rate_cm3_min,
            metrics.machining_time_min,
            metrics.torque_nm,
            metrics.power_kw,
        )
    ):
        # n_adjusted itself was finite and positive, but a low enough
        # available_power_kw can still drive it small enough that a
        # *downstream* division (e.g. length_of_cut_mm / feed_rate_mm_min)
        # overflows to inf even though n_adjusted did not. Report the same
        # infeasible sentinel rather than a result with some finite and
        # some inf/nan fields.
        return _infeasible_sentinel()
    return metrics


def _infeasible_sentinel() -> MillingMetrics:
    """Build a :class:`MillingMetrics` that signals an infeasible power budget.

    Only ``spindle_speed_rpm`` is meaningful: it is deliberately ``nan``
    (fails :func:`math.isfinite`) so the caller
    (``_calculate._compute_metrics()``), which checks
    ``spindle_speed_rpm`` for finiteness/positivity, always converts this
    into a structured ``INFEASIBLE_POWER_BUDGET`` result — even when the
    underlying failure was actually a *downstream* division overflowing
    rather than the spindle speed itself being invalid. No other field is
    ever read by that caller.
    """

    return MillingMetrics(
        spindle_speed_rpm=float("nan"),
        feed_rate_mm_min=float("nan"),
        material_removal_rate_cm3_min=float("nan"),
        machining_time_min=float("nan"),
        torque_nm=float("nan"),
        power_kw=float("nan"),
    )
