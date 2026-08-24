"""Unit tests for shared input validation (T015)."""

import pytest

from machine_calc import UnitSystem, calculate
from machine_calc.config import Configuration
from machine_calc.validation import (
    validate_depth_mm,
    validate_diameter_mm,
    validate_material_present,
    validate_tool_present,
)

CONFIG = Configuration()


def test_diameter_zero_is_invalid():
    error = validate_diameter_mm(0, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DIAMETER"


def test_diameter_negative_is_invalid():
    error = validate_diameter_mm(-5, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DIAMETER"


def test_diameter_within_bounds_is_valid():
    assert validate_diameter_mm(10, CONFIG) is None


def test_diameter_exceeding_default_max_is_invalid():
    error = validate_diameter_mm(150, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DIAMETER"


def test_diameter_at_exact_max_is_valid():
    assert validate_diameter_mm(CONFIG.max_diameter_mm, CONFIG) is None


def test_depth_zero_is_invalid():
    error = validate_depth_mm(0, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DEPTH"


def test_depth_negative_is_invalid():
    error = validate_depth_mm(-1, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DEPTH"


def test_depth_exceeding_default_max_is_invalid():
    error = validate_depth_mm(600, CONFIG)
    assert error is not None
    assert error.code == "INVALID_DEPTH"


def test_depth_within_bounds_is_valid():
    assert validate_depth_mm(25, CONFIG) is None


def test_missing_material_is_invalid():
    error = validate_material_present(None)
    assert error is not None
    assert error.code == "MISSING_MATERIAL"

    error = validate_material_present("")
    assert error is not None
    assert error.code == "MISSING_MATERIAL"


def test_present_material_is_valid():
    assert validate_material_present("Mild Steel") is None


def test_missing_tool_is_invalid():
    error = validate_tool_present(None)
    assert error is not None
    assert error.code == "MISSING_TOOL"


def test_present_tool_is_valid():
    assert validate_tool_present("Carbide") is None


def test_custom_configuration_bounds_are_respected():
    config = Configuration(max_diameter_mm=150.0, max_depth_mm=600.0)
    assert validate_diameter_mm(120, config) is None
    assert validate_depth_mm(550, config) is None


@pytest.mark.parametrize(
    "validate,code",
    [
        (lambda v: validate_diameter_mm(v, CONFIG), "INVALID_DIAMETER"),
        (lambda v: validate_depth_mm(v, CONFIG), "INVALID_DEPTH"),
    ],
)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), None, "10", True])
def test_diameter_and_depth_reject_non_finite_and_non_numeric(validate, code, value):
    """Regression for issue #56.

    ``NaN`` compares ``False`` against both ``<= 0`` and ``> maximum``, so
    before the fix it passed validation and reached the calculation,
    producing a ``NaN``-poisoned result instead of a structured error. The
    same guard also covers ``Infinity``, ``None``, ``bool`` and non-numeric
    values, matching every milling validator
    (``test_validation_milling.test_every_milling_validator_rejects_non_positive_and_non_numeric``).
    """

    error = validate(value)

    assert error is not None
    assert error.code == code


@pytest.mark.parametrize("value", [float("nan"), "10", True, None])
def test_imperial_non_numeric_geometry_returns_error_not_typeerror(value):
    """Regression for the #56 review follow-up.

    Drilling converted imperial lengths with a bare ``in_to_mm()`` before
    validating, so a non-numeric ``diameter`` raised ``TypeError`` from the
    multiplication instead of returning a structured error, violating the
    never-raises contract (FR-015). ``units.to_metric_length()`` now leaves
    such values unconverted so the validators reject them, exactly as
    milling's ``_to_metric()`` already did.
    """

    result = calculate(
        diameter=value,
        depth=1,
        material="Aluminum",
        tool="HSS",
        unit_system=UnitSystem.IMPERIAL,
    )

    assert result.error is not None
    assert result.error.code == "INVALID_DIAMETER"
    assert result.spindle_speed_rpm is None
