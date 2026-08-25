"""Integration test: ``MFGPARAMS_LOCALE`` env var handling at CLI startup
(T026b).

Covers: unset -> English, set to an unrecognized value -> English (no
error), and set to a valid non-English locale (via a test-only fixture
catalog) -> that catalog's text is used.
"""

from __future__ import annotations

import builtins

from mfgparams import i18n
from mfgparams.cli import run

_REPL_INPUTS = [
    "drilling",  # machining operation (009 FR-001)
    "metric",  # unit system
    "standard",  # calculation mode -- no blank/default option (FR-001a)
    "Metal",  # material type
    "Mild Steel",  # material
    "Carbide",  # tool
    "10",  # diameter
    "25",  # depth
    "",  # available power (blank/unknown)
    "n",  # do not run another calculation
]


def _run_repl(monkeypatch):
    inputs = iter(_REPL_INPUTS)
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))


def test_unset_locale_uses_english(monkeypatch, capsys):
    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    i18n.clear_catalog_cache()
    _run_repl(monkeypatch)

    run()

    out = capsys.readouterr().out
    assert "Spindle speed:" in out


def test_unrecognized_locale_falls_back_to_english_without_error(monkeypatch, capsys):
    monkeypatch.setenv("MFGPARAMS_LOCALE", "xx-not-a-real-locale")
    i18n.clear_catalog_cache()
    _run_repl(monkeypatch)

    run()

    out = capsys.readouterr().out
    assert "Spindle speed:" in out
    assert "Error" not in out


def test_valid_non_english_locale_uses_that_catalog(monkeypatch, capsys):
    fixture_key = "cli.result.spindle_speed"
    fixture_catalog = {fixture_key: "Vitesse de broche : {value} RPM"}

    monkeypatch.setenv("MFGPARAMS_LOCALE", "fr-test-fixture")
    i18n.clear_catalog_cache()
    monkeypatch.setitem(i18n._catalog_cache, "fr-test-fixture", fixture_catalog)
    _run_repl(monkeypatch)

    run()

    out = capsys.readouterr().out
    assert "Vitesse de broche :" in out
    assert "Spindle speed:" not in out
