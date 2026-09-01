"""SC-001 prompt-budget test for the milling REPL flow (T023a, T028).

SC-001 caps a complete end-milling run at **14** prompts for the standard
mode, of which at most **12** required a typed value pre-this-feature.
``specs/010-milling-calculation-modes/quickstart.md`` "Per-mode
prompt-count budget" extends this per-mode (research.md #5): standard mode
is 14 prompts / 13 typed (the new mode prompt is itself non-dismissible
per FR-001a, so only the optional power prompt remains dismissible);
power-constrained mode is 14 prompts / 14 typed (the mode prompt adds one,
and the now-required available-power prompt converts from optional to
typed); fixed-RPM mode is 15 prompts / 14 typed (the mode prompt and the
required target-RPM prompt add two, offset by the optional advisory
available-power prompt remaining a single-Enter default).

The exact-count assertions below are a deliberate tripwire: a change that
legitimately adds a prompt must update this test **and** re-check the
budget in quickstart.md, rather than letting the count drift silently up
to (or past) SC-001's ceiling.
"""

import builtins

import pytest

from mfgparams.console.cli import run

#: SC-001's ceiling for the standard mode (unchanged, SC-004).
SC001_MAX_PROMPTS = 14
SC001_MAX_TYPED_VALUES = 13

_END_MILLING_STANDARD_ANSWERS = [
    "milling",
    "end milling",
    "metric",
    "standard",  # calculation mode -- no blank/default option (FR-001a)
    "Metal",
    "Mild Steel",
    "Carbide",
    "10",
    "2",
    "5",
    "0.05",
    "4",
    "100",
    "",  # optional power rating -- dismissible with a bare Enter
]

_END_MILLING_POWER_CONSTRAINED_ANSWERS = [
    "milling",
    "end milling",
    "metric",
    "power-constrained",
    "Metal",
    "Mild Steel",
    "Carbide",
    "10",
    "2",
    "5",
    "0.05",
    "4",
    "100",
    "0.05",  # required available power -- no dismissible prompt in this mode
]

_END_MILLING_FIXED_RPM_ANSWERS = [
    "milling",
    "end milling",
    "metric",
    "fixed-rpm",
    "Metal",
    "Mild Steel",
    "Carbide",
    "10",
    "2",
    "5",
    "0.05",
    "4",
    "100",
    "3000",  # required target RPM
    "",  # optional advisory power rating -- dismissible with a bare Enter
]

_FACE_MILLING_STANDARD_ANSWERS = [
    "milling",
    "face milling",
    "metric",
    "standard",  # calculation mode -- no blank/default option (FR-001a)
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
]

#: (mode label, answers, expected total prompts, expected typed-value prompts).
_MODE_CASES = [
    pytest.param("standard", _END_MILLING_STANDARD_ANSWERS, 14, 13, id="standard"),
    pytest.param(
        "power-constrained", _END_MILLING_POWER_CONSTRAINED_ANSWERS, 14, 14, id="power-constrained"
    ),
    pytest.param("fixed-rpm", _END_MILLING_FIXED_RPM_ANSWERS, 15, 14, id="fixed-rpm"),
]


def _run_and_count(monkeypatch, answers):
    prompts = []
    supply = iter([*answers, "n"])

    def _input(prompt=""):
        prompts.append(prompt)
        return next(supply)

    monkeypatch.setattr(builtins, "input", _input)
    run()
    # Exclude the trailing "run another calculation?" prompt, which is not
    # part of a single calculation run.
    return prompts[:-1]


@pytest.mark.parametrize("mode,answers,expected_total,expected_typed", _MODE_CASES)
def test_end_milling_issues_the_contracted_number_of_prompts_per_mode(
    monkeypatch, capsys, mode, answers, expected_total, expected_typed
):
    prompts = _run_and_count(monkeypatch, answers)
    capsys.readouterr()

    typed = [prompt for prompt, answer in zip(prompts, answers) if answer != ""]

    assert len(prompts) == expected_total, f"{mode}: total prompt count"
    assert len(typed) == expected_typed, f"{mode}: typed prompt count"


def test_standard_mode_stays_within_the_sc001_ceiling(monkeypatch, capsys):
    prompts = _run_and_count(monkeypatch, _END_MILLING_STANDARD_ANSWERS)
    capsys.readouterr()

    typed = [
        prompt for prompt, answer in zip(prompts, _END_MILLING_STANDARD_ANSWERS) if answer != ""
    ]

    assert len(prompts) <= SC001_MAX_PROMPTS
    assert len(typed) <= SC001_MAX_TYPED_VALUES


def test_the_dismissible_prompt_in_standard_mode_is_the_optional_power(monkeypatch, capsys):
    """The one non-typed prompt in standard mode must be the *optional*
    available-power input; the calculation-mode prompt is never
    dismissible (FR-001a)."""

    prompts = _run_and_count(monkeypatch, _END_MILLING_STANDARD_ANSWERS)
    capsys.readouterr()

    dismissed = [
        prompt for prompt, answer in zip(prompts, _END_MILLING_STANDARD_ANSWERS) if answer == ""
    ]

    assert len(dismissed) == 1
    assert "Available power" in dismissed[0]


def test_power_constrained_mode_has_no_dismissible_prompt(monkeypatch, capsys):
    """Every prompt in power-constrained mode requires a typed value (FR-002)."""

    prompts = _run_and_count(monkeypatch, _END_MILLING_POWER_CONSTRAINED_ANSWERS)
    capsys.readouterr()

    dismissed = [
        prompt
        for prompt, answer in zip(prompts, _END_MILLING_POWER_CONSTRAINED_ANSWERS)
        if answer == ""
    ]

    assert dismissed == []


def test_fixed_rpm_mode_the_dismissible_prompt_is_the_optional_available_power(monkeypatch, capsys):
    """FR-008: available power stays optional/advisory in fixed-RPM mode."""

    prompts = _run_and_count(monkeypatch, _END_MILLING_FIXED_RPM_ANSWERS)
    capsys.readouterr()

    dismissed = [
        prompt for prompt, answer in zip(prompts, _END_MILLING_FIXED_RPM_ANSWERS) if answer == ""
    ]

    assert len(dismissed) == 1
    assert "Available power" in dismissed[0]


def test_face_milling_stays_within_the_same_standard_mode_budget(monkeypatch, capsys):
    """Face milling has the same shape, so it must not exceed the ceiling."""

    prompts = _run_and_count(monkeypatch, _FACE_MILLING_STANDARD_ANSWERS)
    capsys.readouterr()

    assert len(prompts) == 14
    assert len(prompts) <= SC001_MAX_PROMPTS
