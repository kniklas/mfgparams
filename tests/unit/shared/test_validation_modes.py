"""Unit tests for validate_target_rpm() and validate_mode_arguments() (T009).

Covers FR-007's target_rpm validation and FR-009's mode-authoritative
MODE_CONFLICT semantics (spec.md Clarifications 2026-07-11 second checklist
follow-up).
"""

import pytest

from mfgparams.models import CalculationMode
from mfgparams.validation import validate_mode_arguments, validate_target_rpm


@pytest.mark.parametrize("bad_rpm", [0, -1, -100.5, float("nan"), float("inf"), float("-inf")])
def test_validate_target_rpm_rejects_invalid_values(bad_rpm):
    error = validate_target_rpm(bad_rpm)
    assert error is not None
    assert error.code == "INVALID_TARGET_RPM"


def test_validate_target_rpm_rejects_non_numeric():
    error = validate_target_rpm("fast")
    assert error is not None
    assert error.code == "INVALID_TARGET_RPM"


@pytest.mark.parametrize("good_rpm", [1, 0.001, 1200, 1_000_000.0])
def test_validate_target_rpm_accepts_positive_finite_values(good_rpm):
    assert validate_target_rpm(good_rpm) is None


def test_validate_target_rpm_accepts_none():
    """A None target_rpm (not supplied) is not itself an error here —
    callers decide whether a missing value is an error for the selected
    mode."""
    assert validate_target_rpm(None) is None


def test_validate_target_rpm_no_upper_bound():
    """spec.md Clarifications 2026-07-11 second checklist follow-up: no
    additional maximum bound beyond finiteness/positivity."""
    assert validate_target_rpm(1e12) is None


def test_mode_conflict_power_constrained_with_target_rpm():
    error = validate_mode_arguments(
        CalculationMode.POWER_CONSTRAINED, available_power=1.0, target_rpm=1200
    )
    assert error is not None
    assert error.code == "MODE_CONFLICT"


def test_mode_conflict_power_constrained_without_available_power():
    error = validate_mode_arguments(
        CalculationMode.POWER_CONSTRAINED, available_power=None, target_rpm=None
    )
    assert error is not None
    assert error.code == "MODE_CONFLICT"


def test_power_constrained_valid_combination_has_no_conflict():
    error = validate_mode_arguments(
        CalculationMode.POWER_CONSTRAINED, available_power=1.0, target_rpm=None
    )
    assert error is None


@pytest.mark.parametrize(
    "bad_power", ["bad", True, False, float("nan"), float("inf"), float("-inf"), 0, -5.0]
)
def test_power_constrained_rejects_non_finite_or_non_positive_available_power(bad_power):
    """A supplied-but-invalid budget can never be met by any spindle
    speed, so it is reported as INFEASIBLE_POWER_BUDGET (matching the
    downstream <= 0 checks in drilling's/milling's _compute_metrics())
    rather than reaching hp_to_kw() or a numeric comparison downstream and
    raising TypeError, which would violate the public API's never-raises
    contract."""

    error = validate_mode_arguments(
        CalculationMode.POWER_CONSTRAINED, available_power=bad_power, target_rpm=None
    )
    assert error is not None
    assert error.code == "INFEASIBLE_POWER_BUDGET"


@pytest.mark.parametrize(
    "available_power,target_rpm",
    [
        (None, None),
        (1.0, None),
        (None, 1200),
        (1.0, 1200),
    ],
)
def test_standard_mode_never_conflicts(available_power, target_rpm):
    """spec.md FR-009 (Clarifications 2026-07-11 second checklist follow-up):
    STANDARD mode ignores any supplied target_rpm/available_power — they
    are simply unused, never a MODE_CONFLICT."""
    error = validate_mode_arguments(
        CalculationMode.STANDARD, available_power=available_power, target_rpm=target_rpm
    )
    assert error is None


@pytest.mark.parametrize(
    "available_power,target_rpm",
    [
        (None, 1200),
        (1.0, 1200),
    ],
)
def test_fixed_rpm_mode_never_conflicts_on_available_power(available_power, target_rpm):
    """available_power remains optional/advisory in FIXED_RPM mode (FR-008)
    — never a conflict, regardless of whether it is supplied."""
    error = validate_mode_arguments(
        CalculationMode.FIXED_RPM, available_power=available_power, target_rpm=target_rpm
    )
    assert error is None


@pytest.mark.parametrize("bad_power", ["bad", True, False, float("nan"), float("inf"), 0, -5.0])
@pytest.mark.parametrize(
    "mode,target_rpm",
    [(CalculationMode.STANDARD, None), (CalculationMode.FIXED_RPM, 1200)],
)
def test_advisory_available_power_rejects_non_finite_or_non_numeric(mode, target_rpm, bad_power):
    """STANDARD/FIXED_RPM only use available_power for an advisory
    feasibility warning (never a hard constraint), but an invalid value
    (non-numeric, bool, non-finite, zero, or negative) must still be
    rejected here — otherwise it would reach hp_to_kw() or a numeric
    comparison against metrics.power_kw downstream and raise TypeError,
    violating the public API's never-raises contract."""
    error = validate_mode_arguments(mode, available_power=bad_power, target_rpm=target_rpm)
    assert error is not None
    assert error.code == "INVALID_AVAILABLE_POWER"


@pytest.mark.parametrize(
    "mode,target_rpm",
    [(CalculationMode.STANDARD, None), (CalculationMode.FIXED_RPM, 1200)],
)
def test_advisory_available_power_accepts_none_or_valid_number(mode, target_rpm):
    assert validate_mode_arguments(mode, available_power=None, target_rpm=target_rpm) is None
    assert validate_mode_arguments(mode, available_power=5.5, target_rpm=target_rpm) is None
