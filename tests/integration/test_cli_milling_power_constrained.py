"""Integration test: REPL power-constrained mode flow for milling (T014).

Selecting the ``power-constrained`` mode prompts for a required available
power and displays the spindle speed with the "adjusted to fit available
power" suffix label (contracts/cli-repl-milling-modes-delta.md). Mirrors
tests/integration/test_cli_power_constrained.py (drilling) for both
``_run_end_milling_session()`` and ``_run_face_milling_session()``.
"""

import builtins

from mfgparams.console.cli import run


def test_end_milling_power_constrained_mode_prompts_for_power_and_labels_result(
    monkeypatch, capsys
):
    inputs = iter(
        [
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
            "0.05",  # required available power (kW)
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "adjusted to fit available power" in out
    assert "0.05 kW" in out


def test_end_milling_power_constrained_infeasible_budget_reprompts(monkeypatch, capsys):
    inputs = iter(
        [
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
            "0",  # invalid available power (must be > 0) -> reprompt
            "0.05",  # valid available power
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please enter a positive numeric value for available power." in out


def test_face_milling_power_constrained_mode_prompts_for_power_and_labels_result(
    monkeypatch, capsys
):
    inputs = iter(
        [
            "milling",
            "face milling",
            "metric",
            "power-constrained",
            "Metal",
            "Mild Steel",
            "Carbide",
            "50",
            "1.5",
            "40",
            "0.15",
            "5",
            "200",
            "0.3",  # required available power (kW)
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "adjusted to fit available power" in out
    assert "0.30 kW" in out
