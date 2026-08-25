"""Contract test: drilling's ``CalculationResult`` stays backward compatible (T042).

Adding ``material_removal_rate`` for milling extends a shared result type
that drilling already returns. FR-002 requires drilling to be unaffected, so
this pins the field order, the new field's default, and the fact that
drilling leaves it ``None`` (research.md decision #7 — MRR is not reported
for drilling).
"""

from __future__ import annotations

import dataclasses

import pytest

from mfgparams import calculate
from mfgparams.models import CalculationResult, UnitSystem

#: Every field drilling relied on before 009, in its original order.
_PRE_EXISTING_FIELDS = [
    "spindle_speed_rpm",
    "feed_rate",
    "machining_time",
    "torque",
    "power_required",
    "unit_system",
    "feasibility_warning",
    "error",
    "mode",
]


def test_pre_existing_fields_keep_their_names_and_order():
    names = [field.name for field in dataclasses.fields(CalculationResult)]

    assert names[: len(_PRE_EXISTING_FIELDS)] == _PRE_EXISTING_FIELDS


def test_material_removal_rate_is_appended_last_and_optional():
    fields = dataclasses.fields(CalculationResult)

    assert fields[-1].name == "material_removal_rate"
    assert fields[-1].default is None


def test_result_is_constructible_without_the_new_field():
    """Existing positional/keyword call sites must keep working unchanged."""

    result = CalculationResult(
        spindle_speed_rpm=1000.0,
        feed_rate=100.0,
        machining_time=1.0,
        torque=5.0,
        power_required=0.5,
        unit_system=UnitSystem.METRIC,
    )

    assert result.material_removal_rate is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"diameter": 10.0, "depth": 25.0, "material": "Mild Steel", "tool": "Carbide"},
        {
            "diameter": 10.0,
            "depth": 25.0,
            "material": "Mild Steel",
            "tool": "Carbide",
            "available_power": 0.01,
        },
    ],
    ids=["standard", "power_warning"],
)
def test_drilling_never_reports_a_material_removal_rate(kwargs):
    result = calculate(**kwargs)

    assert result.error is None
    assert result.spindle_speed_rpm is not None
    assert result.material_removal_rate is None


def test_drilling_error_results_are_unchanged():
    result = calculate(diameter=0.0, depth=25.0, material="Mild Steel", tool="Carbide")

    assert result.error is not None
    assert result.error.code == "INVALID_DIAMETER"
    assert result.material_removal_rate is None
