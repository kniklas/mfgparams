"""Integration test: operation re-selection on the run-again loop (T013, FR-017).

Acceptance Scenario 5: answering "yes" to "run another calculation" returns
the user to the operation prompt, so they may switch operations instead of
being locked into whichever one they picked first.
"""

import builtins

from mfgparams.cli import run

_DRILLING = ["metric", "standard", "Metal", "Mild Steel", "Carbide", "10", "25", ""]
_END_MILLING = [
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
]
_FACE_MILLING = [
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
]


def _prompts(monkeypatch, answers):
    seen = []
    supply = iter(answers)

    def _input(prompt=""):
        seen.append(prompt)
        return next(supply)

    monkeypatch.setattr(builtins, "input", _input)
    return seen


def _operation_prompts(prompts):
    return [p for p in prompts if "Machining operation" in p]


def test_operation_is_asked_again_after_run_again(monkeypatch, capsys):
    prompts = _prompts(monkeypatch, ["drilling", *_DRILLING, "y", "drilling", *_DRILLING, "n"])

    run()
    out = capsys.readouterr().out

    assert len(_operation_prompts(prompts)) == 2
    assert out.count("Spindle speed:") == 2


def test_user_can_switch_from_drilling_to_milling_without_restarting(monkeypatch, capsys):
    prompts = _prompts(monkeypatch, ["drilling", *_DRILLING, "y", "milling", *_END_MILLING, "n"])

    run()
    out = capsys.readouterr().out

    assert len(_operation_prompts(prompts)) == 2
    assert out.count("Spindle speed:") == 2
    # The second pass ran milling: only milling results report a removal rate.
    assert out.count("Material removal:") == 1
    assert "Radial depth of cut" in "".join(prompts)


def test_user_can_switch_from_milling_to_drilling_without_restarting(monkeypatch, capsys):
    _prompts(monkeypatch, ["milling", *_END_MILLING, "y", "drilling", *_DRILLING, "n"])

    run()
    out = capsys.readouterr().out

    assert out.count("Spindle speed:") == 2
    assert out.count("Material removal:") == 1


def test_user_can_switch_milling_sub_operation_on_rerun(monkeypatch, capsys):
    prompts = _prompts(monkeypatch, ["milling", *_END_MILLING, "y", "milling", *_FACE_MILLING, "n"])

    run()
    out = capsys.readouterr().out

    assert out.count("Material removal:") == 2
    joined = "".join(prompts)
    assert "Radial depth of cut" in joined
    assert "Width of cut" in joined


def test_previous_operation_is_offered_as_the_default_but_still_asked(monkeypatch, capsys):
    """FR-017: the choice is re-asked; it is not silently repeated."""

    prompts = _prompts(monkeypatch, ["milling", *_END_MILLING, "y", "", "", *_END_MILLING[1:], "n"])

    run()
    capsys.readouterr()

    operation_prompts = _operation_prompts(prompts)
    assert len(operation_prompts) == 2
    # Second time around, milling is offered as the default.
    assert "(drilling)" in operation_prompts[0]
    assert "(milling)" in operation_prompts[1]


def test_reselecting_the_same_flow_retains_previous_answers_as_defaults(monkeypatch, capsys):
    """Blank answers on the second pass reuse the first pass's values."""

    _prompts(
        monkeypatch,
        [
            "milling",
            *_END_MILLING,
            "y",
            "milling",
            "end milling",
            "",  # unit system defaulted
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            *([""] * 9),  # material type through length of cut, all defaulted
            "",  # available power
            "n",
        ],
    )

    run()
    out = capsys.readouterr().out

    blocks = [b for b in out.split("Spindle speed:") if "Material removal:" in b]
    assert len(blocks) == 2
    # Identical inputs -> identical results.
    assert blocks[0].strip().startswith(blocks[1].strip()[:40])
