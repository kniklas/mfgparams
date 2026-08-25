"""Integration test: identical results between direct calculate() calls and
the CLI for both new modes (T023a; FR-010/FR-016 extension;
/speckit.analyze finding C1).
"""

import builtins

from mfgparams import CalculationMode, calculate
from mfgparams.cli import run


def test_power_constrained_cli_matches_direct_calculate(monkeypatch, capsys):
    expected = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=0.5,
    )
    assert expected.error is None

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
            "0.5",
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert f"{expected.spindle_speed_rpm:.1f} RPM" in out
    assert f"{expected.feed_rate:.1f} mm/min" in out
    assert f"{expected.machining_time:.2f} min" in out
    assert f"{expected.torque:.1f} N\u00b7m" in out
    assert f"{expected.power_required:.2f} kW" in out


def test_fixed_rpm_cli_matches_direct_calculate(monkeypatch, capsys):
    expected = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=500,
    )
    assert expected.error is None

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
            "500",
            "",
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    assert f"{expected.spindle_speed_rpm:.1f} RPM" in out
    assert f"{expected.feed_rate:.1f} mm/min" in out
    assert f"{expected.machining_time:.2f} min" in out
    assert f"{expected.torque:.1f} N\u00b7m" in out
    assert f"{expected.power_required:.2f} kW" in out
