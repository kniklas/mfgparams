"""Additional CLI coverage: invalid unit-system input, imperial flow,
feasibility-warning display, invalid optional power input, and the
``main()`` console-script entry point (rounds out T020-T022 coverage).
"""

import builtins
import sys

from mfgparams.console.cli import main, run


def test_invalid_unit_system_is_reprompted(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "bogus",  # invalid unit system -> reprompt
            "metric",
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            "Metal",  # material type
            "Mild Steel",
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
    assert "Please enter 'metric' or 'imperial'." in out


def test_imperial_flow_displays_imperial_labels(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "imperial",
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "0.4",
            "1.0",
            "",
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "in/min" in out
    assert "in-lb" in out
    assert "HP" in out


def test_feasibility_warning_is_displayed(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "10",
            "25",
            "0.01",  # deliberately low available power
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Warning:" in out


def test_invalid_optional_power_is_ignored(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "10",
            "25",
            "not-a-number",  # invalid power -> ignored, falls back to default
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Ignoring non-numeric power value." in out


def test_main_runs_repl_to_completion(monkeypatch, capsys):
    inputs = iter(
        ["drilling", "metric", "standard", "Metal", "Mild Steel", "Carbide", "10", "25", "", "n"]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(sys, "argv", ["mfgparams"])

    main()

    out = capsys.readouterr().out
    assert "RPM" in out


def test_main_handles_keyboard_interrupt(monkeypatch, capsys):
    def _raise_interrupt(_prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", _raise_interrupt)
    monkeypatch.setattr(sys, "argv", ["mfgparams"])

    main()  # must not propagate the interrupt

    out = capsys.readouterr().out
    assert out == "\n"
