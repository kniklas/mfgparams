"""Contract test: REPL and library produce identical milling numbers (T040).

FR-012 / SC-004: the CLI is a thin presentation layer over the public API, so
driving the REPL and calling the library with the same inputs must yield
exactly the same numeric results — not merely close ones.
"""

import builtins
import re

import pytest

from mfgparams import calculate_end_milling, calculate_face_milling
from mfgparams.console.cli import run

_END_MILLING = {
    "answers": [
        "milling",
        "end milling",
        "metric",
        "standard",
        "Metal",
        "Mild Steel",
        "Carbide",
        "10",
        "2",
        "5",
        "0.05",
        "4",
        "100",
        "",
        "n",
    ],
    "call": lambda: calculate_end_milling(
        diameter=10.0,
        axial_depth_of_cut=2.0,
        radial_depth_of_cut=5.0,
        feed_per_tooth=0.05,
        number_of_teeth=4,
        length_of_cut=100.0,
        material="Mild Steel",
        tool="Carbide",
    ),
}

_FACE_MILLING = {
    "answers": [
        "milling",
        "face milling",
        "metric",
        "standard",
        "Metal",
        "Mild Steel",
        "Carbide",
        "50",
        "1.5",
        "40",
        "0.15",
        "5",
        "200",
        "",
        "n",
    ],
    "call": lambda: calculate_face_milling(
        diameter=50.0,
        axial_depth_of_cut=1.5,
        width_of_cut=40.0,
        feed_per_tooth=0.15,
        number_of_teeth=5,
        length_of_cut=200.0,
        material="Mild Steel",
        tool="Carbide",
    ),
}

_CASES = [
    pytest.param(_END_MILLING, id="end_milling"),
    pytest.param(_FACE_MILLING, id="face_milling"),
]

#: Displayed label -> (result attribute, decimal places used by the CLI).
_DISPLAYED = {
    "Spindle speed": ("spindle_speed_rpm", 1),
    "Feed rate": ("feed_rate", 1),
    "Machining time": ("machining_time", 2),
    "Torque": ("torque", 1),
    "Power required": ("power_required", 2),
    "Material removal": ("material_removal_rate", 2),
}


def _displayed_values(out: str) -> dict:
    values = {}
    for label in _DISPLAYED:
        match = re.search(rf"{label}:\s+(-?[\d.]+)", out)
        assert match, f"{label!r} not found in REPL output"
        values[label] = match.group(1)
    return values


@pytest.mark.parametrize("case", _CASES)
def test_repl_output_matches_the_library_result_exactly(monkeypatch, capsys, case):
    supply = iter(case["answers"])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(supply))

    run()
    displayed = _displayed_values(capsys.readouterr().out)

    result = case["call"]()
    assert result.error is None

    for label, (attribute, places) in _DISPLAYED.items():
        expected = f"{getattr(result, attribute):.{places}f}"
        assert displayed[label] == expected, f"{label} differs"


@pytest.mark.parametrize("case", _CASES)
def test_repl_reports_a_warning_exactly_when_the_library_does(monkeypatch, capsys, case):
    baseline = case["call"]()
    tight = f"{baseline.power_required / 2:.6f}"

    answers = list(case["answers"])
    answers[-2] = tight  # supply a power rating below what is required
    supply = iter(answers)
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(supply))

    run()
    out = capsys.readouterr().out

    assert "Warning:" in out
    # The numeric results are unchanged by the warning.
    displayed = _displayed_values(out)
    assert displayed["Power required"] == f"{baseline.power_required:.2f}"
