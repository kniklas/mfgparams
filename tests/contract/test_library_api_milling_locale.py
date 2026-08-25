"""Contract test: locale handling in the milling library API (T041, FR-019).

The milling entry points follow the same i18n contract as drilling: an
explicit ``locale`` argument wins, ``MFGPARAMS_LOCALE`` is consulted
otherwise, and anything unrecognised falls back to English without raising
(FR-019c/e). Error *codes* are stable identifiers and must never be
translated — only the human-readable ``message`` changes.
"""

from __future__ import annotations

import pytest

from mfgparams import calculate_end_milling, calculate_face_milling, i18n

#: A minimal non-English catalog, registered directly into the cache so the
#: test does not depend on which locales happen to ship with the package.
_FIXTURE_LOCALE = "zz-test-fixture"
_FIXTURE_CATALOG = {
    "error.unknown_material": "[zz] Unknown workpiece material: {material!r}.",
    "error.invalid_mill_diameter.zero": "[zz] Cutter diameter must be greater than 0.",
}

_INVALID_MATERIAL = {
    calculate_end_milling: (10.0, 2.0, 5.0, 0.05, 4, 100.0, "No Such Material", "Carbide"),
    calculate_face_milling: (50.0, 1.5, 40.0, 0.15, 5, 200.0, "No Such Material", "Carbide"),
}
_INVALID_DIAMETER = {
    calculate_end_milling: (0.0, 2.0, 5.0, 0.05, 4, 100.0, "Mild Steel", "Carbide"),
    calculate_face_milling: (0.0, 1.5, 40.0, 0.15, 5, 200.0, "Mild Steel", "Carbide"),
}

_IDS = ["end_milling", "face_milling"]


@pytest.fixture(autouse=True)
def fixture_catalog(monkeypatch):
    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    i18n.clear_catalog_cache()
    monkeypatch.setitem(i18n._catalog_cache, _FIXTURE_LOCALE, _FIXTURE_CATALOG)
    yield
    i18n.clear_catalog_cache()


@pytest.mark.parametrize("fn", _INVALID_MATERIAL, ids=_IDS)
def test_default_locale_is_english(fn):
    result = fn(*_INVALID_MATERIAL[fn])

    assert result.error is not None
    assert result.error.message == "Unknown workpiece material: 'No Such Material'."


@pytest.mark.parametrize("fn", _INVALID_MATERIAL, ids=_IDS)
def test_explicit_locale_argument_selects_the_catalog(fn):
    result = fn(*_INVALID_MATERIAL[fn], locale=_FIXTURE_LOCALE)

    assert result.error is not None
    assert result.error.message == "[zz] Unknown workpiece material: 'No Such Material'."


@pytest.mark.parametrize("fn", _INVALID_DIAMETER, ids=_IDS)
def test_translation_applies_to_validation_errors_too(fn):
    result = fn(*_INVALID_DIAMETER[fn], locale=_FIXTURE_LOCALE)

    assert result.error is not None
    assert result.error.message == "[zz] Cutter diameter must be greater than 0."


@pytest.mark.parametrize("fn", _INVALID_MATERIAL, ids=_IDS)
def test_unknown_locale_falls_back_to_english_without_raising(fn):
    result = fn(*_INVALID_MATERIAL[fn], locale="xx-not-a-real-locale")

    assert result.error is not None
    assert result.error.message == "Unknown workpiece material: 'No Such Material'."


@pytest.mark.parametrize("fn", _INVALID_MATERIAL, ids=_IDS)
def test_locale_falls_back_per_key_when_the_catalog_is_partial(fn):
    """The fixture catalog has no ``error.unknown_tool`` entry."""

    diameter, axial, radial, feed, teeth, length, _material, _tool = (
        *_INVALID_MATERIAL[fn][:6],
        "Mild Steel",
        "No Such Tool",
    )
    result = fn(
        diameter,
        axial,
        radial,
        feed,
        teeth,
        length,
        "Mild Steel",
        "No Such Tool",
        locale=_FIXTURE_LOCALE,
    )

    assert result.error is not None
    assert result.error.message == "Unknown milling tool: 'No Such Tool'."


@pytest.mark.parametrize("fn", _INVALID_MATERIAL, ids=_IDS)
def test_error_codes_are_never_translated(fn):
    english = fn(*_INVALID_MATERIAL[fn])
    translated = fn(*_INVALID_MATERIAL[fn], locale=_FIXTURE_LOCALE)

    assert english.error is not None and translated.error is not None
    assert english.error.code == translated.error.code
    assert english.error.message != translated.error.message
