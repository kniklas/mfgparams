"""Integration test: REPL validation error handling (T021).

Invalid diameter/depth and missing material/tool selections must re-prompt
rather than crash or proceed with bad input.
"""

import builtins

from mfgparams.console.cli import run


def test_invalid_diameter_is_reprompted(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "not-a-number",  # invalid diameter -> reprompt
            "-5",  # invalid diameter (out of range) -> reprompt
            "10",  # valid diameter
            "25",  # valid depth
            "",  # available power
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please enter a numeric value." in out
    assert "Drill diameter must be greater than 0." in out
    assert "RPM" in out  # eventually succeeds


def test_invalid_material_choice_is_reprompted(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            "Metal",  # material type
            "Unknown Material",  # invalid -> reprompt
            "Mild Steel",  # valid
            "Carbide",
            "10",
            "25",
            "",
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please choose one of" in out
    assert "RPM" in out


def test_nan_diameter_and_depth_are_reprompted(monkeypatch, capsys):
    """Regression for issue #56 at the CLI level.

    ``_prompt_number()`` parses the literal ``nan`` successfully (Python's
    ``float("nan")`` does not raise), so the re-prompt has to come from
    ``validate_diameter_mm()``/``validate_depth_mm()`` rejecting the value.
    Before the fix both accepted it and the session printed a
    ``NaN``-poisoned result instead of re-prompting.
    """

    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "nan",  # NaN diameter -> reprompt (issue #56)
            "10",  # valid diameter
            "nan",  # NaN depth -> reprompt (issue #56)
            "25",  # valid depth
            "",  # available power
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Drill diameter must be greater than 0." in out
    assert "Hole depth must be greater than 0." in out
    assert "RPM" in out  # eventually succeeds
    # The successful result must be built from the re-prompted 10/25, not
    # NaN-poisoned: no numeric field may render as "nan".
    assert "nan" not in out.lower()
