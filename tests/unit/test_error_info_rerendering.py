"""Unit test: a `code` shared by two templates re-renders distinctly (SC-006).

`ErrorInfo.code` is coarser than `ErrorInfo.message_key` (FR-006):
`INVALID_DIAMETER` covers both a "value is zero" case and a "value exceeds
max" case (with a parameter), for both drilling and milling. The console
re-renders translated error text from `message_key`/`kwargs`, never from
`code` (FR-005a) — this test proves that re-rendering actually distinguishes
the two cases, using a fixture non-English catalog registered directly into
`mfgparams.console.i18n`'s cache (mirroring the pattern
`tests/contract/test_library_api_milling_locale.py` used before
specs/015-console-i18n-relocation moved this concern to the console).
"""

from __future__ import annotations

import pytest

from mfgparams import calculate_end_milling
from mfgparams.console import i18n as console_i18n

_FIXTURE_LOCALE = "zz-test-fixture"
_FIXTURE_CATALOG = {
    "error.invalid_mill_diameter.zero": "[zz] Cutter diameter must be greater than 0.",
    "error.invalid_mill_diameter.max": (
        "[zz] Cutter diameter must not exceed {max_mill_diameter_mm:g} mm."
    ),
}

_END_MILLING_ARGS = (2.0, 5.0, 0.05, 4, 100.0, "Mild Steel", "Carbide")


@pytest.fixture(autouse=True)
def _fixture_catalog(monkeypatch):
    console_i18n.clear_catalog_cache()
    monkeypatch.setitem(console_i18n._catalog_cache, _FIXTURE_LOCALE, _FIXTURE_CATALOG)
    yield
    console_i18n.clear_catalog_cache()


def _rerender(error, locale):
    return console_i18n.translate(locale, error.message_key, **dict(error.kwargs))


def test_zero_and_max_diameter_share_a_code_but_not_a_message_key():
    zero = calculate_end_milling(0.0, *_END_MILLING_ARGS)
    too_big = calculate_end_milling(1e6, *_END_MILLING_ARGS)

    assert zero.error is not None and too_big.error is not None
    assert zero.error.code == too_big.error.code == "INVALID_DIAMETER"
    assert zero.error.message_key == "error.invalid_mill_diameter.zero"
    assert too_big.error.message_key == "error.invalid_mill_diameter.max"


def test_rerendering_by_message_key_produces_distinct_translated_text():
    zero = calculate_end_milling(0.0, *_END_MILLING_ARGS)
    too_big = calculate_end_milling(1e6, *_END_MILLING_ARGS)

    zero_text = _rerender(zero.error, _FIXTURE_LOCALE)
    too_big_text = _rerender(too_big.error, _FIXTURE_LOCALE)

    assert zero_text == "[zz] Cutter diameter must be greater than 0."
    assert too_big_text == "[zz] Cutter diameter must not exceed 200 mm."
    assert zero_text != too_big_text


def test_rerendering_never_branches_on_code():
    """Two errors with the same `code` but different `message_key` must not collapse."""

    zero = calculate_end_milling(0.0, *_END_MILLING_ARGS)
    too_big = calculate_end_milling(1e6, *_END_MILLING_ARGS)

    # If re-rendering (incorrectly) keyed on `code`, both would resolve to
    # whichever of the two catalog entries `code` happened to map to.
    assert _rerender(zero.error, _FIXTURE_LOCALE) != _rerender(too_big.error, _FIXTURE_LOCALE)
