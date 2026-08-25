"""Integration test: operation-selection prompt ordering (T012, US1).

Acceptance Scenarios 1 and 4: the REPL asks which machining operation to
calculate *before* any operation-specific prompt, and an unrecognized choice
re-prompts with a catalog-sourced message rather than silently defaulting.
"""

import builtins

import pytest

from mfgparams import cli
from mfgparams.cli import run

_DRILLING_ANSWERS = [
    "metric",
    "standard",  # calculation mode -- no blank/default option (FR-001a)
    "Metal",
    "Mild Steel",
    "Carbide",
    "10",
    "25",
    "",  # available power
    "n",  # do not run again
]

_END_MILLING_ANSWERS = [
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
    "",  # available power
    "n",
]


def _prompts(monkeypatch, answers):
    """Feed ``answers`` to ``input()``, recording each prompt string."""

    seen = []
    supply = iter(answers)

    def _input(prompt=""):
        seen.append(prompt)
        return next(supply)

    monkeypatch.setattr(builtins, "input", _input)
    return seen


def test_operation_prompt_is_issued_first(monkeypatch, capsys):
    prompts = _prompts(monkeypatch, ["drilling", *_DRILLING_ANSWERS])

    run()
    capsys.readouterr()

    assert "Machining operation" in prompts[0]
    assert "drilling" in prompts[0] and "milling" in prompts[0]


def test_no_operation_specific_prompt_precedes_the_operation_prompt(monkeypatch, capsys):
    prompts = _prompts(monkeypatch, ["drilling", *_DRILLING_ANSWERS])

    run()
    capsys.readouterr()

    operation_index = next(i for i, p in enumerate(prompts) if "Machining operation" in p)
    for label in ("Material", "Drilling tool", "Unit system", "Drill diameter"):
        first = next((i for i, p in enumerate(prompts) if label in p), None)
        assert first is None or first > operation_index


def test_selecting_milling_prompts_for_the_sub_operation_next(monkeypatch, capsys):
    prompts = _prompts(monkeypatch, ["milling", *_END_MILLING_ANSWERS])

    run()
    capsys.readouterr()

    assert "Machining operation" in prompts[0]
    assert "Milling operation" in prompts[1]
    assert "end milling" in prompts[1] and "face milling" in prompts[1]


def test_unrecognized_operation_is_reprompted(monkeypatch, capsys):
    _prompts(monkeypatch, ["turning", "drilling", *_DRILLING_ANSWERS])

    run()

    out = capsys.readouterr().out
    assert "Please choose one of: drilling, milling" in out
    # It re-prompted rather than silently proceeding with a default.
    assert "Spindle speed:" in out


def test_unrecognized_sub_operation_is_reprompted(monkeypatch, capsys):
    _prompts(monkeypatch, ["milling", "slotting", *_END_MILLING_ANSWERS])

    run()

    out = capsys.readouterr().out
    assert "Please choose one of: end milling, face milling" in out
    assert "Spindle speed:" in out


def test_blank_entry_accepts_the_offered_default(monkeypatch, capsys):
    """A bare Enter takes the default shown in the prompt (drilling)."""

    prompts = _prompts(monkeypatch, ["", *_DRILLING_ANSWERS])

    run()
    out = capsys.readouterr().out

    assert "(drilling)" in prompts[0]
    assert "Drill diameter" in "".join(prompts)
    assert "Spindle speed:" in out


class TestMillingSessionStateResolution:
    """``_MillingSessionState.resolved()`` narrows the prompted inputs."""

    def test_resolved_returns_every_prompted_value(self):
        state = cli._MillingSessionState(
            material="Mild Steel",
            tool="Carbide",
            diameter=10.0,
            axial_depth_of_cut=2.0,
            radial_engagement=5.0,
            feed_per_tooth=0.05,
            number_of_teeth=4,
            length_of_cut=100.0,
        )

        inputs = state.resolved()

        assert inputs.material == "Mild Steel"
        assert inputs.tool == "Carbide"
        assert inputs.diameter == 10.0
        assert inputs.radial_engagement == 5.0
        assert inputs.length_of_cut == 100.0

    def test_resolved_rejects_a_state_that_was_never_prompted(self):
        with pytest.raises(RuntimeError) as excinfo:
            cli._MillingSessionState().resolved()

        message = str(excinfo.value)
        assert "diameter" in message and "material" in message

    def test_resolved_names_only_the_missing_inputs(self):
        state = cli._MillingSessionState(
            material="Mild Steel",
            tool="Carbide",
            diameter=10.0,
            axial_depth_of_cut=2.0,
            radial_engagement=5.0,
            feed_per_tooth=0.05,
            number_of_teeth=4,
        )

        with pytest.raises(RuntimeError) as excinfo:
            state.resolved()

        message = str(excinfo.value)
        assert "length_of_cut" in message
        assert "diameter" not in message
