"""Unit tests for unit conversion helpers (T016)."""

import math

from mfgparams.models import UnitSystem
from mfgparams.units import (
    N_PER_LBF,
    ft_min_to_m_min,
    hp_to_kw,
    in_lb_to_nm,
    in_to_mm,
    kw_to_hp,
    lbf_to_n,
    m_min_to_ft_min,
    mm_to_in,
    n_per_mm2_to_psi,
    n_to_lbf,
    nm_to_in_lb,
    psi_to_n_per_mm2,
    to_metric_power,
)


def test_mm_in_round_trip():
    original = 25.0
    assert math.isclose(in_to_mm(mm_to_in(original)), original, rel_tol=1e-9)


def test_mm_to_in_known_value():
    assert math.isclose(mm_to_in(25.4), 1.0, rel_tol=1e-6)


def test_in_to_mm_known_value():
    assert math.isclose(in_to_mm(1.0), 25.4, rel_tol=1e-9)


def test_nm_in_lb_round_trip():
    original = 3.1
    assert math.isclose(in_lb_to_nm(nm_to_in_lb(original)), original, rel_tol=1e-6)


def test_kw_hp_round_trip():
    original = 0.44
    assert math.isclose(hp_to_kw(kw_to_hp(original)), original, rel_tol=1e-6)


def test_kw_to_hp_known_value():
    assert math.isclose(kw_to_hp(1.0), 1.34102, rel_tol=1e-3)


# --- New conversion helpers (specs/005-configurable-materials-tools T007/T008) ---


def test_ft_min_m_min_round_trip():
    original = 250.0
    assert math.isclose(m_min_to_ft_min(ft_min_to_m_min(original)), original, rel_tol=1e-9)


def test_ft_min_to_m_min_known_value():
    # Quickstart Scenario 5: 250 ft/min ~= 76.2 m/min.
    assert math.isclose(ft_min_to_m_min(250.0), 76.2, rel_tol=1e-3)


def test_m_min_to_ft_min_known_value():
    assert math.isclose(m_min_to_ft_min(76.2), 250.0, rel_tol=1e-3)


def test_ft_min_to_m_min_zero():
    assert math.isclose(ft_min_to_m_min(0.0), 0.0, abs_tol=1e-12)


def test_ft_min_to_m_min_near_zero_positive():
    value = 1e-6
    assert math.isclose(m_min_to_ft_min(ft_min_to_m_min(value)), value, rel_tol=1e-6, abs_tol=1e-12)


def test_psi_n_per_mm2_round_trip():
    original = 130000.0
    assert math.isclose(n_per_mm2_to_psi(psi_to_n_per_mm2(original)), original, rel_tol=1e-6)


def test_psi_to_n_per_mm2_known_value():
    # Quickstart Scenario 5: 130000 psi ~= 896.3 N/mm^2.
    assert math.isclose(psi_to_n_per_mm2(130000.0), 896.3, rel_tol=1e-3)


def test_n_per_mm2_to_psi_known_value():
    assert math.isclose(n_per_mm2_to_psi(1.0), 145.037738, rel_tol=1e-6)


def test_psi_to_n_per_mm2_zero():
    assert math.isclose(psi_to_n_per_mm2(0.0), 0.0, abs_tol=1e-12)


def test_n_lbf_round_trip():
    original = 798.0
    assert math.isclose(lbf_to_n(n_to_lbf(original)), original, rel_tol=1e-9)


def test_n_to_lbf_known_value():
    assert math.isclose(n_to_lbf(N_PER_LBF), 1.0, rel_tol=1e-9)


def test_lbf_to_n_known_value():
    assert math.isclose(lbf_to_n(1.0), 4.4482216152605, rel_tol=1e-9)


def test_to_metric_power_metric_is_identity():
    assert to_metric_power(5.0, UnitSystem.METRIC) == 5.0


def test_to_metric_power_imperial_converts_hp_to_kw():
    assert math.isclose(to_metric_power(1.0, UnitSystem.IMPERIAL), hp_to_kw(1.0), rel_tol=1e-9)


def test_to_metric_power_passes_through_non_numeric_and_bool_unconverted():
    """Mirrors to_metric_length()'s identical guard (issue #56): a
    non-numeric or bool value is left unconverted so downstream
    _is_positive_finite_number-based validators reject it with a
    structured error instead of this call raising TypeError."""
    assert to_metric_power("fast", UnitSystem.IMPERIAL) == "fast"
    assert to_metric_power(True, UnitSystem.IMPERIAL) is True
    assert to_metric_power(None, UnitSystem.IMPERIAL) is None


def test_to_metric_power_arbitrary_precision_int_becomes_infinity_not_overflowerror():
    """Copilot review finding on specs/019-turning-calculations PR #100:
    an oversized positive Python int supplied as imperial available_power
    previously reached hp_to_kw() and raised OverflowError during
    int-to-float conversion. Unlike to_metric_length() (which returns the
    value unconverted, relying on a downstream maximum-bound validator
    available power has none of), math.inf is returned instead — the
    mathematically sensible "effectively unlimited power" value, safe in
    every downstream comparison/division."""
    assert to_metric_power(10**1000, UnitSystem.IMPERIAL) == math.inf
