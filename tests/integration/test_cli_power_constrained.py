"""Integration test: REPL power-constrained mode flow (T013).

Selecting the ``power-constrained`` mode prompts for a required available
power and displays the spindle speed with the "adjusted to fit available
power" suffix label (contracts/cli-repl-delta.md).
"""

import builtins

from mfgparams.console.cli import run


def test_power_constrained_mode_prompts_for_power_and_labels_result(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",  # unit system
            "power-constrained",  # calculation mode
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "10",
            "25",
            "0.5",  # required available power (kW)
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "adjusted to fit available power" in out
    assert "0.50 kW" in out


def test_power_constrained_infeasible_budget_shows_error(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "power-constrained",
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "10",
            "25",
            "0",  # invalid available power (must be > 0) -> reprompt
            "0.5",  # valid available power
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please enter a positive numeric value for available power." in out


def test_power_constrained_non_finite_power_is_reprompted(monkeypatch, capsys):
    """``inf``/``nan`` at the required-power prompt must re-prompt, the
    same as the fixed-RPM target-RPM prompt, rather than reaching the
    library as a spuriously "valid" (but non-finite) budget."""

    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "power-constrained",
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "10",
            "25",
            "inf",  # non-finite -> reprompt, not an infeasible-budget result
            "0.5",  # valid available power
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please enter a positive numeric value for available power." in out
    assert "adjusted to fit available power" in out
