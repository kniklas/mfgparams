"""Integration test: REPL loop, changing one input and recalculating without
restarting the process (T022; FR-014, spec Acceptance Scenario 4).
"""

import builtins

from mfgparams.cli import run


def test_loop_allows_changing_tool_and_recalculating(monkeypatch, capsys):
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            "Metal",  # material type
            "Mild Steel",
            "HSS",
            "10",
            "25",
            "",
            "y",  # run another calculation
            "drilling",  # machining operation (009 FR-001)
            "metric",  # unit system unchanged (default reused)
            "standard",  # calculation mode -- no blank/default option (FR-001a)
            "",  # material type unchanged (reuse previous default)
            "",  # material unchanged (reuse previous default)
            "Carbide",  # switch drilling tool
            "",  # diameter unchanged
            "",  # depth unchanged
            "",  # power unchanged
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))

    run()

    out = capsys.readouterr().out
    # Two full result blocks should have been printed (one per calculation).
    assert out.count("Spindle speed:") == 2
