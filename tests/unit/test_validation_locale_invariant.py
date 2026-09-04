"""Unit test: `validation.py`'s functions are locale-invariant by construction
(specs/015-console-i18n-relocation FR-005).

A Copilot review on the implementing PR found that FR-005's "ErrorInfo
.message is always English" invariant was only true because every *caller*
of `validation.py` happened to pass `DEFAULT_LOCALE` — nothing in
`validation.py` itself enforced it. Since these functions are public
(`from mfgparams.validation import validate_diameter_mm` works), a direct
caller passing a non-English `locale` would have received a non-English
`message`, contradicting the invariant documented on `ErrorInfo` and relied
on by `CalculationResult.error`.

This test calls a representative sample directly with a registered
non-English fixture catalog and a non-default `locale=` argument, proving
the message stays English regardless — the invariant now holds inside
`validation.py`, not just at its callers.
"""

from __future__ import annotations

import pytest

from mfgparams import i18n
from mfgparams.config import Configuration
from mfgparams.models import CalculationMode
from mfgparams.validation import (
    validate_depth_of_cut_mm,
    validate_diameter_mm,
    validate_material_present,
    validate_mode_arguments,
)

_FIXTURE_LOCALE = "zz-validation-fixture"
_FIXTURE_CATALOG = {
    "error.invalid_diameter.zero": "[zz] must be positive",
    "error.missing_material": "[zz] material required",
    "error.invalid_depth_of_cut.zero": "[zz] {label} must be positive",
    "cli.label.axial_depth_of_cut": "[zz] profondeur",
    "error.mode_conflict": "[zz] conflict",
}

_CONFIG = Configuration()


@pytest.fixture(autouse=True)
def _fixture_catalog(monkeypatch):
    i18n.clear_catalog_cache()
    monkeypatch.setitem(i18n._catalog_cache, _FIXTURE_LOCALE, _FIXTURE_CATALOG)
    yield
    i18n.clear_catalog_cache()


def test_validate_diameter_mm_ignores_a_direct_non_english_locale():
    error = validate_diameter_mm(0.0, _CONFIG, locale=_FIXTURE_LOCALE)
    assert error is not None
    assert error.message == "Drill diameter must be greater than 0."


def test_validate_material_present_ignores_a_direct_non_english_locale():
    error = validate_material_present(None, locale=_FIXTURE_LOCALE)
    assert error is not None
    assert error.message == "A workpiece material must be selected."


def test_validate_depth_of_cut_mm_ignores_a_direct_non_english_locale_including_the_label():
    """The embedded `{label}` must also stay English, not just the template."""

    error = validate_depth_of_cut_mm(0.0, _CONFIG, locale=_FIXTURE_LOCALE)
    assert error is not None
    assert error.message == "Axial depth of cut must be greater than 0."
    assert "profondeur" not in error.message


def test_validate_mode_arguments_ignores_a_direct_non_english_locale():
    error = validate_mode_arguments(
        CalculationMode.POWER_CONSTRAINED, None, 100.0, locale=_FIXTURE_LOCALE
    )
    assert error is not None
    assert error.message.startswith("Power-constrained and fixed-RPM inputs")
