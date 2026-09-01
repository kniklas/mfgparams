"""Integration test: the face-milling REPL flow (T033, US3).

Acceptance Scenarios 1 and 4: the flow prompts for a **width of cut** (not a
radial depth of cut), uses the face-mill tool registry, and warns when the
supplied power rating is exceeded.
"""

import builtins

from mfgparams.console.cli import run

_ANSWERS = [
    "milling",
    "face milling",
    "metric",
    "standard",
    "Metal",
    "Mild Steel",
    "Carbide",
    "50",  # cutter diameter
    "1.5",  # axial depth of cut
    "40",  # width of cut
    "0.15",  # feed per tooth
    "5",  # number of inserts
    "200",  # length of cut
]

_EXPECTED_PROMPT_ORDER = [
    "Machining operation",
    "Milling operation",
    "Unit system",
    "Calculation mode",
    "Material type",
    "Material",
    "Face-mill tool",
    "Cutter diameter",
    "Axial depth of cut",
    "Width of cut",
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

    for expected, prompt in zip(_EXPECTED_PROMPT_ORDER, prompts):
        assert expected in prompt, f"expected {expected!r} in {prompt!r}"


def test_width_of_cut_label_is_used_instead_of_radial_depth_of_cut(monkeypatch, capsys):
    prompts = _prompts(monkeypatch, [*_ANSWERS, "", "n"])

    run()
    capsys.readouterr()

    joined = "".join(prompts)
    assert "Width of cut" in joined
    assert "Radial depth of cut" not in joined


def test_face_mill_registry_is_offered_not_the_end_mill_one(monkeypatch, capsys):
    prompts = _prompts(monkeypatch, [*_ANSWERS, "", "n"])

    run()
    capsys.readouterr()

    tool_prompt = next(p for p in prompts if "Face-mill tool" in p)
    # "Cermet" is bundled for face milling only; "Cobalt" for end milling only.
    assert "Cermet" in tool_prompt
    assert "Cobalt" not in tool_prompt


def test_result_block_includes_the_material_removal_rate(monkeypatch, capsys):
    _prompts(monkeypatch, [*_ANSWERS, "", "n"])

    run()
    out = capsys.readouterr().out

    assert "Material removal:" in out
    assert "cm³/min" in out


def test_feasibility_warning_when_the_supplied_rating_is_exceeded(monkeypatch, capsys):
    _prompts(monkeypatch, [*_ANSWERS, "0.01", "n"])

    run()
    out = capsys.readouterr().out

    assert "Warning:" in out
    assert "Power required:" in out


def test_no_warning_when_the_supplied_rating_is_sufficient(monkeypatch, capsys):
    _prompts(monkeypatch, [*_ANSWERS, "50", "n"])

    run()
    out = capsys.readouterr().out

    assert "Warning:" not in out
    assert "Spindle speed:" in out


def test_width_above_the_cutter_diameter_is_reprompted(monkeypatch, capsys):
    answers = [
        "milling",
        "face milling",
        "metric",
        "standard",
        "Metal",
        "Mild Steel",
        "Carbide",
        "40",  # cutter diameter
        "1.5",
        "45",  # width > diameter -> reprompt (FR-009)
        "30",  # corrected
        "0.15",
        "5",
        "200",
        "",
        "n",
    ]
    _prompts(monkeypatch, answers)

    run()
    out = capsys.readouterr().out

    assert "Width of cut must not exceed the cutter diameter" in out
    assert "Spindle speed:" in out
