"""Integration test: ``MFGPARAMS_LOCALE`` env var handling at CLI startup
(T026b).

Covers: unset -> English, set to an unrecognized value -> English (no
error), and set to a valid non-English locale (via a test-only fixture
catalog) -> that catalog's text is used.
"""

from __future__ import annotations

import builtins

from mfgparams import i18n
from mfgparams.console import i18n as console_i18n
from mfgparams.console.cli import run

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
    console_i18n.clear_catalog_cache()
    _run_repl(monkeypatch)

    run()

    out = capsys.readouterr().out
    assert "Spindle speed:" in out


def test_unrecognized_locale_falls_back_to_english_without_error(monkeypatch, capsys):
    monkeypatch.setenv("MFGPARAMS_LOCALE", "xx-not-a-real-locale")
    i18n.clear_catalog_cache()
    console_i18n.clear_catalog_cache()
    _run_repl(monkeypatch)

    run()

    out = capsys.readouterr().out
    assert "Spindle speed:" in out
    assert "Error" not in out


def test_valid_non_english_locale_translates_an_error_result(monkeypatch, capsys):
    """FR-005a end-to-end: `_display_result`'s error branch (`console/cli.py`
    `_render_error` at the final result, not just the immediate re-prompt
    paths already covered by unit tests) actually re-renders through the
    console's catalogue when a non-English locale is active. A Copilot
    review on the implementing PR found this specific wiring — as opposed
    to `_render_error` itself — had no test driving it end-to-end: the unit
    tests call `_render_error` directly, and the other locale integration
    tests here only ever reach a *successful* result.

    ``0.0001`` kW is a positive available power (passes the prompt-time
    ``> 0`` check) but infeasible for any real drilling job, so the run
    reaches ``INFEASIBLE_POWER_BUDGET`` at the final result rather than a
    prompt-time reprompt.
    """

    fixture_catalog = {
        "error.calculation_overflow": "[zz] résultat trop grand",
    }
    inputs = iter(
        [
            "milling",
            "end milling",
            "metric",
            "standard",
            "Metal",
            "Mild Steel",
            "Carbide",
            "10",  # cutter diameter
            "2",  # axial depth of cut
            "5",  # radial depth of cut
            "1e308",  # feed per tooth -- individually "valid" (positive,
            #            finite), but overflows feed_rate_mm_min downstream
            "4",  # number of teeth
            "100",  # length of cut
            "",  # available power (blank/unknown)
            "n",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(inputs))
    monkeypatch.setenv("MFGPARAMS_LOCALE", "fr-error-fixture")
    i18n.clear_catalog_cache()
    console_i18n.clear_catalog_cache()
    monkeypatch.setitem(console_i18n._catalog_cache, "fr-error-fixture", fixture_catalog)

    run()

    out = capsys.readouterr().out
    assert "[zz] résultat trop grand" in out
    assert "too large to represent" not in out


def test_valid_non_english_locale_uses_that_catalog(monkeypatch, capsys):
    # cli.result.spindle_speed is console-owned (specs/015-console-i18n
    # -relocation FR-001), so the fixture catalog must be registered in the
    # console's own cache, not core's — the console renders it via
    # mfgparams.console.i18n, which has a separate cache from mfgparams.i18n.
    fixture_key = "cli.result.spindle_speed"
    fixture_catalog = {fixture_key: "Vitesse de broche : {value} RPM"}

    monkeypatch.setenv("MFGPARAMS_LOCALE", "fr-test-fixture")
    i18n.clear_catalog_cache()
    console_i18n.clear_catalog_cache()
    monkeypatch.setitem(console_i18n._catalog_cache, "fr-test-fixture", fixture_catalog)
    _run_repl(monkeypatch)

    run()

    out = capsys.readouterr().out
    assert "Vitesse de broche :" in out
    assert "Spindle speed:" not in out
