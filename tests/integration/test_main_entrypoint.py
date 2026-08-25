"""Smoke test for `python -m mfgparams` entry point (T025)."""

import subprocess
import sys


def test_module_entrypoint_runs_and_exits_cleanly():
    proc = subprocess.run(
        [sys.executable, "-m", "mfgparams"],
        input="drilling\nmetric\nstandard\nMetal\nMild Steel\nCarbide\n10\n25\n\nn\n",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    assert "RPM" in proc.stdout
