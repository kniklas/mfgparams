"""Integration test: CLI fixed-RPM mode selection for milling (T021).

Selecting the ``fixed-rpm`` mode prompts for a required target spindle
speed (RPM), followed by the existing optional advisory available-power
prompt, and the result display labels the spindle speed as
"user-specified" (contracts/cli-repl-milling-modes-delta.md). Mirrors
tests/integration/test_cli_fixed_rpm.py (drilling) for both milling
sessions.
"""

import builtins

from mfgparams.console.cli import run


def test_end_milling_fixed_rpm_mode_prompts_for_target_rpm_and_labels_result(monkeypatch, capsys):
    inputs = iter(
        [
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
            "",  # optional advisory available power (blank/unknown)
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "3000.0 RPM" in out
    assert "user-specified" in out


def test_end_milling_fixed_rpm_invalid_target_rpm_is_reprompted(monkeypatch, capsys):
    inputs = iter(
        [
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
            "-5",  # invalid target RPM -> reprompt
            "not-a-number",  # invalid target RPM -> reprompt
            "3000",  # valid target RPM
            "",
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please enter a positive numeric value for target spindle speed." in out
    assert "3000.0 RPM" in out


def test_face_milling_fixed_rpm_mode_prompts_for_target_rpm_and_labels_result(monkeypatch, capsys):
    inputs = iter(
        [
            "milling",
            "face milling",
            "metric",
            "fixed-rpm",
            "Metal",
            "Mild Steel",
            "Carbide",
            "50",
            "1.5",
            "40",
            "0.15",
            "5",
            "200",
            "500",  # required target RPM
            "",  # optional advisory available power (blank/unknown)
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "500.0 RPM" in out
    assert "user-specified" in out
