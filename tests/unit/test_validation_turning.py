"""Unit tests for the turning-specific validators (specs/019-turning-calculations FR-010).

Covers ``validate_turning_diameter_mm``, ``validate_turning_depth_of_cut_mm``
(including its workpiece-radius check), and ``validate_turning_length_of_cut_mm``.
"""

import pytest

from mfgparams.config import Configuration
from mfgparams.validation import (
    validate_turning_depth_of_cut_mm,
    validate_turning_diameter_mm,
    validate_turning_length_of_cut_mm,
)

CONFIG = Configuration()


@pytest.mark.parametrize(
    "validate,code",
    [
        (lambda v: validate_turning_diameter_mm(v, CONFIG), "INVALID_DIAMETER"),
        (lambda v: validate_turning_depth_of_cut_mm(v, 100.0, CONFIG), "INVALID_DEPTH_OF_CUT"),
        (lambda v: validate_turning_length_of_cut_mm(v, CONFIG), "INVALID_LENGTH_OF_CUT"),
    ],
)
@pytest.mark.parametrize(
    "value", [0, -1, float("nan"), float("inf"), float("-inf"), None, "10", True]
)
def test_every_turning_validator_rejects_non_positive_and_non_numeric(validate, code, value):
    error = validate(value)

    assert error is not None
    assert error.code == code


def test_turning_diameter_accepts_nominal_value():
    assert validate_turning_diameter_mm(40.0, CONFIG) is None


def test_turning_diameter_rejects_exceeding_configured_maximum():
    error = validate_turning_diameter_mm(CONFIG.max_turning_diameter_mm + 1, CONFIG)

    assert error is not None
    assert error.code == "INVALID_DIAMETER"
    assert "exceed" in error.message


def test_turning_depth_of_cut_accepts_nominal_value():
    assert validate_turning_depth_of_cut_mm(2.0, 40.0, CONFIG) is None


def test_turning_depth_of_cut_rejects_exceeding_configured_maximum():
    error = validate_turning_depth_of_cut_mm(CONFIG.max_turning_depth_of_cut_mm + 1, 1000.0, CONFIG)

    assert error is not None
    assert error.code == "INVALID_DEPTH_OF_CUT"
    assert "exceed" in error.message


@pytest.mark.parametrize("depth_of_cut, diameter", [(5.0, 10.0), (6.0, 10.0), (5.5, 11.0)])
def test_turning_depth_of_cut_rejects_at_or_beyond_workpiece_radius(depth_of_cut, diameter):
    """A depth of cut >= the workpiece radius is physically impossible
    (spec.md Edge Cases): it would remove more material than the
    workpiece's radius has."""

    error = validate_turning_depth_of_cut_mm(depth_of_cut, diameter, CONFIG)

    assert error is not None
    assert error.code == "INVALID_DEPTH_OF_CUT"
    assert "radius" in error.message


def test_turning_depth_of_cut_accepts_just_under_workpiece_radius():
    # radius is 5.0mm for a 10mm diameter; 4.9mm is comfortably under it.
    assert validate_turning_depth_of_cut_mm(4.9, 10.0, CONFIG) is None


def test_turning_depth_of_cut_radius_check_skipped_for_invalid_diameter():
    """When the diameter itself is invalid, the radius comparison is
    skipped rather than comparing against a nonsensical value -- the
    diameter's own validator is responsible for reporting that failure."""

    assert validate_turning_depth_of_cut_mm(2.0, -1.0, CONFIG) is None
    assert validate_turning_depth_of_cut_mm(2.0, float("nan"), CONFIG) is None


def test_turning_length_of_cut_accepts_nominal_value():
    assert validate_turning_length_of_cut_mm(100.0, CONFIG) is None


def test_turning_length_of_cut_rejects_exceeding_configured_maximum():
    error = validate_turning_length_of_cut_mm(CONFIG.max_turning_length_of_cut_mm + 1, CONFIG)

    assert error is not None
    assert error.code == "INVALID_LENGTH_OF_CUT"
    assert "exceed" in error.message


def test_turning_bounds_are_distinct_from_milling_bounds():
    """Turning's depth-of-cut/length-of-cut bounds must not be aliases of
    milling's shared fields -- research.md #3 found milling's
    max_depth_of_cut_mm (50mm) is too permissive for turning's realistic
    single-pass depth of cut."""

    assert CONFIG.max_turning_depth_of_cut_mm != CONFIG.max_depth_of_cut_mm
    assert CONFIG.max_turning_diameter_mm != CONFIG.max_diameter_mm
    assert CONFIG.max_turning_diameter_mm != CONFIG.max_mill_diameter_mm
