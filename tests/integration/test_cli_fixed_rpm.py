"""Integration test: CLI fixed-RPM mode selection (T020).

Selecting the ``fixed-rpm`` mode prompts for a required target spindle
speed (RPM), followed by the existing optional advisory available-power
prompt, and the result display labels the spindle speed as "user-specified"
(contracts/cli-repl-delta.md).
"""

import builtins

from mfgparams.cli import run


def test_fixed_rpm_mode_prompts_for_target_rpm_and_labels_result(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",  # unit system
            "fixed-rpm",  # calculation mode
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "10",
            "25",
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


def test_fixed_rpm_invalid_target_rpm_is_reprompted(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "fixed-rpm",
            "Metal",  # material type
            "Mild Steel",
            "Carbide",
            "10",
            "25",
            "-5",  # invalid target RPM -> reprompt
            "not-a-number",  # invalid target RPM -> reprompt
            "500",  # valid target RPM
            "",
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert "Please enter a positive numeric value for target spindle speed." in out
    assert "500.0 RPM" in out
