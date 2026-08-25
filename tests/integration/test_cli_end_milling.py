"""Integration test: the end-milling REPL flow (T023, US2).

Acceptance Scenarios 1, 5 and 6: the full prompt sequence of
``contracts/cli-repl-milling.md`` "End milling session prompts", the result
block including the new material-removal-rate line, and the feasibility
warning behaviour with and without a supplied power rating.
"""

import builtins

from mfgparams.cli import run

_ANSWERS = [
    "milling",
    "end milling",
    "metric",
    "standard",
    "Metal",
    "Mild Steel",
    "Carbide",
    "10",  # cutter diameter
    "2",  # axial depth of cut
    "5",  # radial depth of cut
    "0.05",  # feed per tooth
    "4",  # number of teeth
    "100",  # length of cut
]

_EXPECTED_PROMPT_ORDER = [
    "Machining operation",
    "Milling operation",
    "Unit system",
    "Calculation mode",
    "Material type",
    "Material",
    "End-mill tool",
    "Cutter diameter",
    "Axial depth of cut",
    "Radial depth of cut",
    "Feed per tooth",
    "Number of teeth",
    "Length of cut",
    "Available power",
]


def _prompts(monkeypatch, answers):
    seen = []
    supply = iter(answers)

    def _input(prompt=""):
        seen.append(prompt)
        return next(supply)

    monkeypatch.setattr(builtins, "input", _input)
    return seen


def test_prompt_sequence_matches_the_contract(monkeypatch, capsys):
    prompts = _prompts(monkeypatch, [*_ANSWERS, "", "n"])

    run()
    capsys.readouterr()

    # Drop the trailing run-again prompt before comparing.
    actual = prompts[: len(_EXPECTED_PROMPT_ORDER)]
    for expected, prompt in zip(_EXPECTED_PROMPT_ORDER, actual):
        assert expected in prompt, f"expected {expected!r} in {prompt!r}"


def test_calculation_mode_prompt_defaults_to_standard(monkeypatch, capsys):
    """The mode prompt is offered (FR-001a), but the default (standard) keeps
    the rest of the flow byte-for-byte unchanged from 009-milling-calculations
    (SC-004)."""

    prompts = _prompts(monkeypatch, [*_ANSWERS, "", "n"])

    run()
    capsys.readouterr()

    assert any("Calculation mode" in p for p in prompts)


def test_result_block_includes_the_material_removal_rate(monkeypatch, capsys):
    _prompts(monkeypatch, [*_ANSWERS, "", "n"])

    run()
    out = capsys.readouterr().out

    assert "Spindle speed:" in out
    assert "Feed rate:" in out
    assert "Machining time:" in out
    assert "Torque:" in out
    assert "Power required:" in out
    assert "Material removal:" in out
    assert "cm³/min" in out


def test_power_is_reported_when_no_rating_is_supplied(monkeypatch, capsys):
    """Omitting the optional rating must not suppress the power figure."""

    _prompts(monkeypatch, [*_ANSWERS, "", "n"])

    run()
    out = capsys.readouterr().out

    assert "Power required:" in out
    assert "exceeds" not in out


def test_feasibility_warning_when_the_supplied_rating_is_exceeded(monkeypatch, capsys):
    _prompts(monkeypatch, [*_ANSWERS, "0.01", "n"])

    run()
    out = capsys.readouterr().out

    assert "Warning:" in out
    # The numbers are still shown alongside the warning (FR-011).
    assert "Power required:" in out
    assert "Material removal:" in out


def test_no_warning_when_the_supplied_rating_is_sufficient(monkeypatch, capsys):
    _prompts(monkeypatch, [*_ANSWERS, "50", "n"])

    run()
    out = capsys.readouterr().out

    assert "Warning:" not in out
    assert "Power required:" in out


def test_radial_depth_above_the_diameter_is_reprompted(monkeypatch, capsys):
    answers = [
        "milling",
        "end milling",
        "metric",
        "standard",
        "Metal",
        "Mild Steel",
        "Carbide",
        "10",
        "2",
        "12",  # radial depth > diameter -> reprompt (FR-009)
        "5",  # corrected
        "0.05",
        "4",
        "100",
        "",
        "n",
    ]
    _prompts(monkeypatch, answers)

    run()
    out = capsys.readouterr().out

    assert "Radial depth of cut must not exceed the cutter diameter" in out
    assert "Spindle speed:" in out


def test_fractional_tooth_count_is_reprompted(monkeypatch, capsys):
    answers = [
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
        "4.5",  # fractional -> reprompt (FR-008)
        "4",
        "100",
        "",
        "n",
    ]
    _prompts(monkeypatch, answers)

    run()
    out = capsys.readouterr().out

    assert "whole number" in out
    assert "Spindle speed:" in out


def test_imperial_flow_uses_imperial_labels(monkeypatch, capsys):
    answers = [
        "milling",
        "end milling",
        "imperial",
        "standard",
        "Metal",
        "Mild Steel",
        "Carbide",
        "0.5",
        "0.1",
        "0.25",
        "0.002",
        "4",
        "4",
        "",
        "n",
    ]
    _prompts(monkeypatch, answers)

    run()
    out = capsys.readouterr().out

    assert "in/min" in out
    assert "in-lb" in out
    assert "HP" in out
    assert "in³/min" in out
