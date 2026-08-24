"""Shared metric<->imperial conversion helpers (FR-017; research.md #4).

All calculations are performed canonically in metric internally; these
helpers convert user-supplied imperial inputs to metric before calculation,
and convert metric results to imperial for display/output when
``UnitSystem.IMPERIAL`` is selected.
"""

from __future__ import annotations

from machine_calc.models import UnitSystem

MM_PER_INCH = 25.4
CM3_PER_IN3 = 16.387064
NM_PER_IN_LB = 1.0 / 8.850745791327185
HP_PER_KW = 1.3410220895
M_PER_FT = 0.3048
PSI_PER_MPA = 145.037738  # N/mm^2 == MPa (specs/005-configurable-materials-tools/research.md #5)


def mm_to_in(value_mm: float) -> float:
    """Convert millimeters to inches."""

    return value_mm / MM_PER_INCH


def in_to_mm(value_in: float) -> float:
    """Convert inches to millimeters."""

    return value_in * MM_PER_INCH


def to_metric_length(value: float, unit_system: UnitSystem) -> float:
    """Convert a length input to canonical mm when the caller used imperial.

    Non-numeric, ``None``, and ``bool`` values are passed through
    unconverted rather than fed to :func:`in_to_mm`, which would either
    raise (``None``/strings) or silently coerce (``True``/``False``).
    Leaving them unconverted lets the downstream
    ``_is_positive_finite_number``-based validators in
    :mod:`machine_calc.validation` reject them with the documented
    structured error instead of the call raising ``TypeError``, per the
    never-raises contract (FR-012/FR-015).

    Shared by drilling and milling so both operations' imperial paths
    behave identically for such inputs (issue #56 review follow-up);
    milling introduced this guard first, as ``_to_metric()``.
    """

    if unit_system is not UnitSystem.IMPERIAL:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    try:
        return in_to_mm(value)
    except OverflowError:
        # An int too large to coerce to a C double (e.g. ``10**1000``).
        # Returned unconverted: it is far beyond every configured maximum
        # either way, so the validators still reject it with the documented
        # bound error instead of the conversion raising.
        return value


def cm3_min_to_in3_min(value_cm3_min: float) -> float:
    """Convert a volumetric rate from cm^3/min to in^3/min.

    1 in^3 = 16.387064 cm^3 exactly (derived from the exact
    1 in = 25.4 mm definition). Used to report a milling material removal
    rate under ``UnitSystem.IMPERIAL``
    (specs/009-milling-calculations/research.md #7).
    """

    return value_cm3_min / CM3_PER_IN3


def in3_min_to_cm3_min(value_in3_min: float) -> float:
    """Convert a volumetric rate from in^3/min to cm^3/min.

    1 in^3 = 16.387064 cm^3 exactly; the inverse of
    :func:`cm3_min_to_in3_min`.
    """

    return value_in3_min * CM3_PER_IN3


def nm_to_in_lb(value_nm: float) -> float:
    """Convert newton-meters to inch-pounds."""

    return value_nm * 8.850745791327185


def in_lb_to_nm(value_in_lb: float) -> float:
    """Convert inch-pounds to newton-meters."""

    return value_in_lb * NM_PER_IN_LB


def kw_to_hp(value_kw: float) -> float:
    """Convert kilowatts to horsepower."""

    return value_kw * HP_PER_KW


def hp_to_kw(value_hp: float) -> float:
    """Convert horsepower to kilowatts."""

    return value_hp / HP_PER_KW


def ft_min_to_m_min(value_ft_min: float) -> float:
    """Convert feet-per-minute to meters-per-minute (1 ft = 0.3048 m).

    Used to convert an imperial-declared ``reference_cutting_speed``
    (specs/005-configurable-materials-tools/research.md #5) to the
    canonical metric m/min unit used internally.
    """

    return value_ft_min * M_PER_FT


def m_min_to_ft_min(value_m_min: float) -> float:
    """Convert meters-per-minute to feet-per-minute (1 ft = 0.3048 m)."""

    return value_m_min / M_PER_FT


def psi_to_n_per_mm2(value_psi: float) -> float:
    """Convert pounds-per-square-inch (psi) to N/mm^2 (== MPa).

    1 MPa = 145.037738 psi (specs/005-configurable-materials-tools/
    research.md #5). Used to convert an imperial-declared
    ``specific_cutting_force`` to the canonical metric N/mm^2 unit used
    internally.
    """

    return value_psi / PSI_PER_MPA


def n_per_mm2_to_psi(value_n_per_mm2: float) -> float:
    """Convert N/mm^2 (== MPa) to pounds-per-square-inch (psi).

    1 MPa = 145.037738 psi (specs/005-configurable-materials-tools/
    research.md #5).
    """

    return value_n_per_mm2 * PSI_PER_MPA
