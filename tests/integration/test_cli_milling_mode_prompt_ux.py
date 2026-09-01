"""Integration test: milling mode-prompt UX edge cases (T014a).

Covers invalid-mode re-prompting (an unrecognized mode entry MUST
re-prompt, never silently fall back to a default), the blank-required-
available-power-prompt re-prompt behavior in power-constrained mode
(asserting it is never treated as ``MODE_CONFLICT``), and FR-013's
loop-mode-switch clearing behavior for milling. Mirrors
tests/integration/test_cli_mode_prompt_ux.py (drilling) — depends on
T015, T016.
"""

import builtins

from mfgparams.console.cli import run


def test_invalid_mode_choice_is_reprompted(monkeypatch, capsys):
    inputs = iter(
        [
            "milling",
            "end milling",
            "metric",
            "bogus-mode",  # invalid -> reprompt
            "standard",  # explicit mode; blank has no default to accept (FR-001a)
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
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please choose one of" in out
    assert "recommended" in out


def test_blank_mode_choice_is_reprompted(monkeypatch, capsys):
    """A blank entry at the mode prompt MUST re-prompt, never silently
    accept a default (spec.md Clarifications 2026-08-19; FR-001a)."""

    inputs = iter(
        [
            "milling",
            "end milling",
            "metric",
            "",  # blank -> must reprompt, not silently accept a default
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
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please choose one of" in out


def test_blank_required_available_power_is_reprompted_not_a_mode_conflict(monkeypatch, capsys):
    """A blank answer to the *required* available-power prompt in
    power-constrained mode must simply re-prompt for a positive number — it
    must never surface as a MODE_CONFLICT error (that error is reserved for
    library-level argument combinations, not REPL input gaps)."""

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
            "",  # blank -> reprompt (required in this mode)
            "0.05",  # valid available power
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "MODE_CONFLICT" not in out
    assert "Please enter a numeric value." in out
    assert "adjusted to fit available power" in out


def test_switching_mode_on_loop_rerun_clears_previous_mode_values(monkeypatch, capsys):
    inputs = iter(
        [
            "milling",
            "end milling",
            "metric",
            "power-constrained",  # first iteration: power-constrained
            "Metal",
            "Mild Steel",
            "Carbide",
            "10",
            "2",
            "5",
            "0.05",
            "4",
            "100",
            "0.05",  # required available power
            "y",  # run another calculation
            "milling",
            "end milling",
            "metric",
            "fixed-rpm",  # switch mode -> must clear available_power default
            "",  # material type unchanged
            "",  # material unchanged
            "",  # tool unchanged
            "",  # diameter unchanged
            "",  # axial depth unchanged
            "",  # radial depth unchanged
            "",  # feed per tooth unchanged
            "",  # number of teeth unchanged
            "",  # length of cut unchanged
            "3000",  # required target RPM (no stale power default reused)
            "",  # optional advisory power now blank (was cleared, not "0.05")
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "adjusted to fit available power" in out
    assert "user-specified" in out
