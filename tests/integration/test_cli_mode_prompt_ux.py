"""Integration test: mode-prompt UX edge cases (T013a).

Covers invalid-mode re-prompting (spec.md Clarifications 2026-07-11: an
unrecognized mode entry MUST re-prompt, never silently fall back to a
default) and FR-013's loop-mode-switch clearing behavior (switching modes
on a subsequent loop iteration clears the previous mode's target-RPM /
available-power values rather than carrying them over as defaults).

Drilling's mode prompt (spec 002) treats a blank entry the same as
material/tool selection: it accepts the current default. This is
deliberately unlike milling's mode prompt (spec 010, Clarifications
2026-08-19), which has no blank/default option at all — see
``test_cli_milling_mode_prompt_ux.py`` for that behavior.
"""

import builtins

from mfgparams.console.cli import run


def test_invalid_mode_choice_is_reprompted(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "bogus-mode",  # invalid -> reprompt
            "",  # blank -> accepts default (standard)
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
    assert "Please choose one of" in out
    assert "recommended" in out


def test_blank_mode_choice_accepts_the_current_default(monkeypatch, capsys):
    """A blank entry at drilling's mode prompt accepts the current default,
    the same as material/tool selection (spec 002 Clarifications
    2026-07-11) — unlike milling's mode prompt, which has no blank/default
    option (spec 010 Clarifications 2026-08-19)."""

    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "",  # blank -> accepts the current default (standard)
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
    assert "Please choose one of" not in out
    assert "recommended" in out


def test_switching_mode_on_loop_rerun_clears_previous_mode_values(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "power-constrained",  # first iteration: power-constrained
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "10",
            "25",
            "0.5",  # required available power
            "y",  # run another calculation
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "fixed-rpm",  # switch mode -> must clear available_power default
            "",  # material type unchanged
            "",  # material unchanged
            "",  # tool unchanged
            "",  # diameter unchanged
            "",  # depth unchanged
            "500",  # required target RPM (no stale power default reused)
            "",  # optional advisory power now blank (was cleared, not "0.5")
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "adjusted to fit available power" in out
    assert "user-specified" in out
