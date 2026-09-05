"""Contract test: locale handling in the milling and drilling library API
(T041, FR-019; specs/015-console-i18n-relocation FR-005/FR-005b/FR-007).

Since specs/015-console-i18n-relocation, ``CalculationResult.error.message``
is always English, regardless of ``MFGPARAMS_LOCALE`` or an explicit
``locale=`` argument — this is what keeps the library API usable without the
``console`` extra installed (FR-005). The ``locale`` parameter is retained
on the public functions for signature compatibility only (spec.md
Assumptions); it no longer affects any returned text. Non-English rendering
is now the console's responsibility, driven by ``ErrorInfo.message_key`` and
``ErrorInfo.kwargs`` rather than by this library-level parameter (FR-005a) —
that re-rendering path is covered separately, in
``tests/unit/test_error_info_rerendering.py`` (SC-006), not here.

Error *codes* remain stable identifiers, unaffected by any of this
(FR-006).
"""

from __future__ import annotations

import pytest

from mfgparams import calculate, calculate_end_milling, calculate_face_milling, i18n

#: Drilling shares the exact same fix (specs/015-console-i18n-relocation
#: T013): its `calculate()` also pins message construction to English via a
#: `message_locale` name distinct from the caller's `locale`. A Copilot
#: review finding on an earlier version of this file noted that only
#: end/face milling were exercised here, so a drilling-only regression
#: (threading the caller's locale back into drilling's errors) would pass
#: this whole suite undetected. `calculate` (drilling) is included in every
#: locale-invariant check below for that reason; its diameter-specific
#: kwarg shape differs from milling's (`max_diameter_mm`, not
#: `max_mill_diameter_mm`), so it is deliberately not added to
#: `_INVALID_DIAMETER`, which asserts milling's exact kwarg shape.
_INVALID_MATERIAL = {
    calculate: (10.0, 25.0, "No Such Material", "Carbide"),
    calculate_end_milling: (10.0, 2.0, 5.0, 0.05, 4, 100.0, "No Such Material", "Carbide"),
    calculate_face_milling: (50.0, 1.5, 40.0, 0.15, 5, 200.0, "No Such Material", "Carbide"),
}
_INVALID_DIAMETER = {
    calculate_end_milling: (0.0, 2.0, 5.0, 0.05, 4, 100.0, "Mild Steel", "Carbide"),
    calculate_face_milling: (0.0, 1.5, 40.0, 0.15, 5, 200.0, "Mild Steel", "Carbide"),
}

_IDS = ["drilling", "end_milling", "face_milling"]
_MILLING_IDS = ["end_milling", "face_milling"]

#: A *core* fixture catalog, registered directly into `mfgparams.i18n`'s
#: cache, so this module doesn't depend on a real non-English locale
#: shipping. Without this, every locale in a naive "try some other locales"
#: list falls back to English anyway (core only bundles "en"), and a test
#: asserting "message is English" would pass whether or not the fix that is
#: supposed to make it true actually exists — a Copilot review finding on an
#: earlier version of this file. Registering fixture non-English text for a
#: key under test is what makes "still English" a meaningful assertion: if
#: `locale=` were still threaded into message construction, this catalog's
#: text — not the real English text — would appear instead.
_FIXTURE_LOCALE = "zz-core-fixture"
_FIXTURE_CORE_CATALOG = {
    "error.unknown_material": "[zz] N'existe pas: {material!r}.",
}

_NON_ENGLISH_LOCALES = [_FIXTURE_LOCALE, "xx-not-a-real-locale", ""]


@pytest.fixture(autouse=True)
def _clear_locale_env(monkeypatch):
    monkeypatch.delenv("MFGPARAMS_LOCALE", raising=False)
    i18n.clear_catalog_cache()
    monkeypatch.setitem(i18n._catalog_cache, _FIXTURE_LOCALE, _FIXTURE_CORE_CATALOG)
    yield
    i18n.clear_catalog_cache()


@pytest.mark.parametrize("fn", _INVALID_MATERIAL, ids=_IDS)
def test_default_locale_is_english(fn):
    result = fn(*_INVALID_MATERIAL[fn])

    assert result.error is not None
    assert result.error.message == "Unknown workpiece material: 'No Such Material'."
    assert result.error.message_key == "error.unknown_material"
    assert result.error.kwargs == (("material", "No Such Material"),)


@pytest.mark.parametrize("fn", _INVALID_MATERIAL, ids=_IDS)
@pytest.mark.parametrize("locale", _NON_ENGLISH_LOCALES)
def test_locale_argument_no_longer_affects_the_message(fn, locale):
    """FR-005/FR-007: ``message`` is English no matter what ``locale=`` is."""

    result = fn(*_INVALID_MATERIAL[fn], locale=locale)

    assert result.error is not None
    assert result.error.message == "Unknown workpiece material: 'No Such Material'."


@pytest.mark.parametrize("fn", _INVALID_MATERIAL, ids=_IDS)
def test_locale_env_var_no_longer_affects_the_message(fn, monkeypatch):
    """FR-005/FR-007: ``MFGPARAMS_LOCALE`` no longer affects ``message`` either."""

    monkeypatch.setenv("MFGPARAMS_LOCALE", _FIXTURE_LOCALE)
    result = fn(*_INVALID_MATERIAL[fn])

    assert result.error is not None
    assert result.error.message == "Unknown workpiece material: 'No Such Material'."


@pytest.mark.parametrize("fn", _INVALID_DIAMETER, ids=_MILLING_IDS)
def test_message_key_and_kwargs_are_populated_for_a_parameterized_message(fn):
    """FR-005b: the max-diameter case carries the parameter as ``kwargs``."""

    diameter, axial, radial, feed, teeth, length, material, tool = _INVALID_DIAMETER[fn]
    too_big = fn(1e6, axial, radial, feed, teeth, length, material, tool)

    assert too_big.error is not None
    assert too_big.error.message_key == "error.invalid_mill_diameter.max"
    assert too_big.error.kwargs == (("max_mill_diameter_mm", 200.0),)
    assert "200" in too_big.error.message


@pytest.mark.parametrize("fn", _INVALID_DIAMETER, ids=_MILLING_IDS)
def test_a_code_shared_by_two_templates_has_distinct_message_keys(fn):
    """FR-006: ``INVALID_DIAMETER`` covers a zero case and a too-big case."""

    zero = fn(*_INVALID_DIAMETER[fn])
    too_big_args = (1e6, *_INVALID_DIAMETER[fn][1:])
    too_big = fn(*too_big_args)

    assert zero.error is not None and too_big.error is not None
    assert zero.error.code == too_big.error.code == "INVALID_DIAMETER"
    assert zero.error.message_key != too_big.error.message_key


@pytest.mark.parametrize("fn", _INVALID_MATERIAL, ids=_IDS)
def test_error_codes_and_message_are_identical_regardless_of_locale(fn):
    """Nothing about ``ErrorInfo`` varies with ``locale=`` any more (FR-005/FR-007)."""

    english = fn(*_INVALID_MATERIAL[fn])
    other_locale = fn(*_INVALID_MATERIAL[fn], locale=_FIXTURE_LOCALE)

    assert english.error is not None and other_locale.error is not None
    assert english.error.code == other_locale.error.code
    assert english.error.message == other_locale.error.message
    assert english.error.message_key == other_locale.error.message_key
    assert english.error.kwargs == other_locale.error.kwargs
