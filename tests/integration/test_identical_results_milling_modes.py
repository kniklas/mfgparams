"""Contract test: REPL and library produce identical numbers for the new
milling calculation modes (T024a; FR-010 extension).

Extends tests/contract/test_identical_results_milling.py's STANDARD-mode
proof to POWER_CONSTRAINED and FIXED_RPM, for both milling
sub-operations: driving the REPL with the same inputs and mode selection
as a direct library call must yield exactly the same numeric results.
"""

import builtins
import re

from mfgparams import CalculationMode, calculate_end_milling, calculate_face_milling
from mfgparams.cli import run

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


def _assert_matches(monkeypatch, capsys, answers, call):
    supply = iter(answers)
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(supply))

    run()
    displayed = _displayed_values(capsys.readouterr().out)

    result = call()
    assert result.error is None

    for label, (attribute, places) in _DISPLAYED.items():
        expected = f"{getattr(result, attribute):.{places}f}"
        assert displayed[label] == expected, f"{label} differs"


_END_MILLING_BASE = dict(
    diameter=10.0,
    axial_depth_of_cut=2.0,
    radial_depth_of_cut=5.0,
    feed_per_tooth=0.05,
    number_of_teeth=4,
    length_of_cut=100.0,
    material="Mild Steel",
    tool="Carbide",
)

_FACE_MILLING_BASE = dict(
    diameter=50.0,
    axial_depth_of_cut=1.5,
    width_of_cut=40.0,
    feed_per_tooth=0.15,
    number_of_teeth=5,
    length_of_cut=200.0,
    material="Mild Steel",
    tool="Carbide",
)

_END_MILLING_ANSWER_PREFIX = [
    "milling",
    "end milling",
    "metric",
]
_END_MILLING_GEOMETRY_ANSWERS = [
    "Metal",
    "Mild Steel",
    "Carbide",
    "10",
    "2",
    "5",
    "0.05",
    "4",
    "100",
]

_FACE_MILLING_ANSWER_PREFIX = [
    "milling",
    "face milling",
    "metric",
]
_FACE_MILLING_GEOMETRY_ANSWERS = [
    "Metal",
    "Mild Steel",
    "Carbide",
    "50",
    "1.5",
    "40",
    "0.15",
    "5",
    "200",
]


def test_end_milling_power_constrained_repl_matches_library(monkeypatch, capsys):
    answers = [
        *_END_MILLING_ANSWER_PREFIX,
        "power-constrained",
        *_END_MILLING_GEOMETRY_ANSWERS,
        "0.05",
        "n",
    ]
    _assert_matches(
        monkeypatch,
        capsys,
        answers,
        lambda: calculate_end_milling(
            **_END_MILLING_BASE,
            mode=CalculationMode.POWER_CONSTRAINED,
            available_power=0.05,
        ),
    )


def test_end_milling_fixed_rpm_repl_matches_library(monkeypatch, capsys):
    answers = [
        *_END_MILLING_ANSWER_PREFIX,
        "fixed-rpm",
        *_END_MILLING_GEOMETRY_ANSWERS,
        "3000",
        "",
        "n",
    ]
    _assert_matches(
        monkeypatch,
        capsys,
        answers,
        lambda: calculate_end_milling(
            **_END_MILLING_BASE,
            mode=CalculationMode.FIXED_RPM,
            target_rpm=3000,
        ),
    )


def test_face_milling_power_constrained_repl_matches_library(monkeypatch, capsys):
    answers = [
        *_FACE_MILLING_ANSWER_PREFIX,
        "power-constrained",
        *_FACE_MILLING_GEOMETRY_ANSWERS,
        "0.3",
        "n",
    ]
    _assert_matches(
        monkeypatch,
        capsys,
        answers,
        lambda: calculate_face_milling(
            **_FACE_MILLING_BASE,
            mode=CalculationMode.POWER_CONSTRAINED,
            available_power=0.3,
        ),
    )


def test_face_milling_fixed_rpm_repl_matches_library(monkeypatch, capsys):
    answers = [
        *_FACE_MILLING_ANSWER_PREFIX,
        "fixed-rpm",
        *_FACE_MILLING_GEOMETRY_ANSWERS,
        "500",
        "",
        "n",
    ]
    _assert_matches(
        monkeypatch,
        capsys,
        answers,
        lambda: calculate_face_milling(
            **_FACE_MILLING_BASE,
            mode=CalculationMode.FIXED_RPM,
            target_rpm=500,
        ),
    )
