"""Unit tests for the milling-specific validators (T011b, FR-008).

Focused on ``validate_tooth_count()``'s whole-number rule, which is the one
milling validator whose behaviour is not a straight port of an existing
drilling check.
"""

import pytest

from mfgparams.config import Configuration
from mfgparams.validation import (
    validate_depth_of_cut_mm,
    validate_engagement_mm,
    validate_feed_per_tooth_mm,
    validate_length_of_cut_mm,
    validate_mill_diameter_mm,
    validate_tooth_count,
)

CONFIG = Configuration()


@pytest.mark.parametrize("value", [1, 2, 4, 12, 4.0, 1.0])
def test_whole_tooth_counts_are_accepted(value):
    assert validate_tooth_count(value) is None


@pytest.mark.parametrize("value", [4.5, 0.5, 3.0001, 2.75])
def test_fractional_tooth_counts_are_rejected(value):
    error = validate_tooth_count(value)

    assert error is not None
    assert error.code == "INVALID_TOOTH_COUNT"
    assert "whole number" in error.message


@pytest.mark.parametrize("value", [0, -1, -4.0])
def test_non_positive_tooth_counts_are_rejected(value):
    error = validate_tooth_count(value)

    assert error is not None
    assert error.code == "INVALID_TOOTH_COUNT"
    # Non-positive counts get the "greater than 0" message, not the
    # "whole number" one, so the user is told the actual problem.
    assert "whole number" not in error.message


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), None, "4", True])
def test_non_numeric_tooth_counts_are_rejected(value):
    error = validate_tooth_count(value)

    assert error is not None
    assert error.code == "INVALID_TOOTH_COUNT"


@pytest.mark.parametrize(
    "validate,code",
    [
        (lambda v: validate_mill_diameter_mm(v, CONFIG), "INVALID_DIAMETER"),
        (lambda v: validate_depth_of_cut_mm(v, CONFIG), "INVALID_DEPTH_OF_CUT"),
        (validate_feed_per_tooth_mm, "INVALID_FEED_PER_TOOTH"),
        (lambda v: validate_length_of_cut_mm(v, CONFIG), "INVALID_LENGTH_OF_CUT"),
    ],
)
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), None, "10"])
def test_every_milling_validator_rejects_non_positive_and_non_numeric(validate, code, value):
    error = validate(value)

    assert error is not None
    assert error.code == code


def test_depth_of_cut_message_names_the_input_being_validated():
    axial = validate_depth_of_cut_mm(-1, CONFIG, "en", "cli.label.axial_depth_of_cut")
    width = validate_depth_of_cut_mm(-1, CONFIG, "en", "cli.label.width_of_cut")

    assert "Axial depth of cut" in axial.message
    assert "Width of cut" in width.message


def test_engagement_defers_to_the_depth_validator_for_non_positive_values():
    """FR-009's check only concerns the diameter relation (validation order)."""

    assert validate_engagement_mm(0, 10.0) is None
    assert validate_engagement_mm(-5, 10.0) is None


def test_engagement_equal_to_the_diameter_is_allowed():
    assert validate_engagement_mm(10.0, 10.0) is None


def test_engagement_above_the_diameter_is_rejected_not_clamped():
    error = validate_engagement_mm(10.1, 10.0)

    assert error is not None
    assert error.code == "INVALID_ENGAGEMENT"
    assert "10 mm" in error.message
