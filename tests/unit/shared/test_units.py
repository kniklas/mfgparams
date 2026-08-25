"""Unit tests for unit conversion helpers (T016)."""

import math

from mfgparams.units import (
    ft_min_to_m_min,
    hp_to_kw,
    in_lb_to_nm,
    in_to_mm,
    kw_to_hp,
    m_min_to_ft_min,
    mm_to_in,
    n_per_mm2_to_psi,
    nm_to_in_lb,
    psi_to_n_per_mm2,
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
