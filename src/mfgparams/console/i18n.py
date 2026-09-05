"""Message catalog loader and locale resolution for the console.

Mirrors :mod:`mfgparams.i18n` exactly in structure and contract, scoped to
:mod:`mfgparams.console.locales` instead of :mod:`mfgparams.locales`
(specs/015-console-i18n-relocation research.md #1 — a deliberate duplicate,
not a shared module, because the two catalogs have different compatibility
contracts: core's is public-API surface, console's is presentation and can
change freely).

Provides:

- :func:`get_locale`: reads ``MFGPARAMS_LOCALE``, resolved against the
  console's own bundled catalogs. Callers that need a *fixed-for-session*
  locale (the console itself) MUST call this exactly once at startup and
  hold the result for the lifetime of that session.
- :func:`translate`: looks up a message by ID for a given locale, falling
  back to the console's English catalog for any missing locale or key, and
  substituting ``str.format()``-style named placeholders. Never raises to
  the caller — a missing placeholder value is logged (in English) rather
  than surfaced as an exception.

This module intentionally contains no user-facing English text itself; all
strings live in ``mfgparams.console.locales.*`` catalog modules.

Does **not** duplicate :func:`mfgparams.i18n.get_raw_locale`: that function
has no catalog dependency (it resolves ``MFGPARAMS_LOCALE`` verbatim, for
data-driven lookups such as ``WorkpieceMaterial.translations``) and stays a
``mfgparams.i18n`` import wherever it is used — those lookups are Story 3 of
specs/015-console-i18n-relocation and are untouched by this catalog split.
"""

from __future__ import annotations

import importlib
import logging
import os

DEFAULT_LOCALE = "en"
_LOCALE_ENV_VAR = "MFGPARAMS_LOCALE"

_logger = logging.getLogger(__name__)

# Cache of locale -> catalog dict (or None if the locale has no bundled
# module). A plain dict (rather than functools.lru_cache) so tests can
# register/clear fixture catalogs deterministically.
_catalog_cache: dict[str, dict[str, str] | None] = {}


def _load_catalog(locale: str) -> dict[str, str] | None:
    """Load the ``MESSAGES`` dict from ``mfgparams.console.locales.<locale>``.

    Returns ``None`` if no such bundled locale module exists. Results are
    cached per locale for the process lifetime.
    """

    if locale in _catalog_cache:
        return _catalog_cache[locale]

    try:
        module = importlib.import_module(f"mfgparams.console.locales.{locale}")
    except ImportError:
        _catalog_cache[locale] = None
        return None

    catalog = getattr(module, "MESSAGES", None)
    _catalog_cache[locale] = catalog
    return catalog


def clear_catalog_cache() -> None:
    """Clear the locale catalog cache (test support only)."""

    _catalog_cache.clear()


def get_locale() -> str:
    """Resolve the active locale from ``MFGPARAMS_LOCALE``, against the
    console's own bundled catalogs.

    Returns the environment variable's value if it is non-empty and matches
    a bundled locale module; otherwise returns :data:`DEFAULT_LOCALE`
    (``"en"``). No OS/system locale (``LANG``/``LC_ALL``) auto-detection is
    performed. The console MUST call this function exactly once per session
    and hold the result, exactly as :func:`mfgparams.i18n.get_locale`
    requires of its own callers.
    """

    raw = os.environ.get(_LOCALE_ENV_VAR, "")
    if raw and _load_catalog(raw) is not None:
        return raw
    return DEFAULT_LOCALE


def has_message(locale: str, key: str) -> bool:
    """Report whether ``key`` resolves to a real catalog entry.

    Uses the same lookup order as :func:`translate` (``locale`` first, then
    the English catalog) but stops before formatting. See
    :func:`mfgparams.i18n.has_message`'s docstring for why this is needed
    rather than comparing ``translate``'s result against the key.
    """

    catalog = _load_catalog(locale)
    if catalog is not None and key in catalog:
        return True
    english = _load_catalog(DEFAULT_LOCALE) or {}
    return key in english


def translate(locale: str, key: str, **kwargs: object) -> str:
    """Look up and format message ``key`` for ``locale``.

    Falls back to the console's English catalog if ``locale`` has no
    bundled module or lacks ``key``. If a placeholder required by the
    message template is missing from ``kwargs``, this function does NOT
    raise; instead it logs a warning (in English) and returns the
    unformatted template as a usable fallback.
    """

    catalog = _load_catalog(locale)
    template = catalog.get(key) if catalog else None

    if template is None:
        english = _load_catalog(DEFAULT_LOCALE) or {}
        template = english.get(key, key)

    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        _logger.warning(
            "i18n: missing or invalid placeholder value for message key %r "
            "(locale=%r); returning unformatted template",
            key,
            locale,
        )
        return template
