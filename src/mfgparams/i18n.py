"""Message catalog loader and locale resolution (FR-019a-e; Constitution VIII).

Provides:

- :func:`get_locale`: reads ``MFGPARAMS_LOCALE`` (FR-019c). Callers that
  need a *fixed-for-session* locale (the CLI) MUST call this exactly once at
  startup and hold the result for the lifetime of that session; the library
  API instead calls it once per :func:`mfgparams.calculate` invocation
  (or accepts an explicit ``locale`` argument), since it has no persistent
  session concept.
- :func:`translate`: looks up a message by ID for a given locale, falling
  back to the English catalog for any missing locale or key (FR-019e), and
  substituting ``str.format()``-style named placeholders (FR-019b). Never
  raises to the caller — a missing placeholder value is logged (in English,
  per FR-019f) rather than surfaced as an exception.

This module intentionally contains no user-facing English text itself; all
strings live in ``mfgparams.locales.*`` catalog modules (FR-019a).
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
    """Load the ``MESSAGES`` dict from ``mfgparams.locales.<locale>``.

    Returns ``None`` if no such bundled locale module exists. Results are
    cached per locale for the process lifetime.
    """

    if locale in _catalog_cache:
        return _catalog_cache[locale]

    try:
        module = importlib.import_module(f"mfgparams.locales.{locale}")
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
    """Resolve the active locale from ``MFGPARAMS_LOCALE`` (FR-019c).

    Returns the environment variable's value if it is non-empty and matches
    a bundled locale module; otherwise returns :data:`DEFAULT_LOCALE`
    (``"en"``). No OS/system locale (``LANG``/``LC_ALL``) auto-detection is
    performed. Callers that need a locale fixed for a whole session (e.g.
    the CLI) MUST call this function exactly once and hold the result.
    """

    raw = os.environ.get(_LOCALE_ENV_VAR, "")
    if raw and _load_catalog(raw) is not None:
        return raw
    return DEFAULT_LOCALE


def get_raw_locale() -> str:
    """Return ``MFGPARAMS_LOCALE`` verbatim, without requiring a bundled catalog.

    Unlike :func:`get_locale`, this does **not** fall back to
    :data:`DEFAULT_LOCALE` merely because no ``mfgparams.locales.<raw>``
    message-catalog module exists — it is intended for **data-driven**
    lookups (e.g. ``WorkpieceMaterial.display_name``/``DrillingTool.
    display_name``, specs/005-configurable-materials-tools research.md #7)
    that resolve translations from configuration data, not the message
    catalog, and so must not be gated on a catalog module's existence.
    Returns :data:`DEFAULT_LOCALE` only if the environment variable is
    unset/empty.
    """

    return os.environ.get(_LOCALE_ENV_VAR, "") or DEFAULT_LOCALE


def has_message(locale: str, key: str) -> bool:
    """Report whether ``key`` resolves to a real catalog entry.

    Uses the same lookup order as :func:`translate` (``locale`` first, then
    the English catalog) but stops before formatting. Callers building a
    message key from user-supplied data need this: passing such a key to
    :func:`translate` and comparing the result against the key cannot
    reliably detect a miss, because ``translate`` formats the fallback
    template — which *is* the key — and logs a warning when that formatting
    fails on stray braces.

    Args:
        locale: The locale to look the key up in.
        key: The message-catalog key.

    Returns:
        ``True`` if the key exists in the locale's catalog or in the English
        fallback catalog, else ``False``.
    """

    catalog = _load_catalog(locale)
    if catalog is not None and key in catalog:
        return True
    english = _load_catalog(DEFAULT_LOCALE) or {}
    return key in english


def translate(locale: str, key: str, **kwargs: object) -> str:
    """Look up and format message ``key`` for ``locale``.

    Falls back to the English catalog if ``locale`` has no bundled module
    or lacks ``key`` (FR-019e). If a placeholder required by the message
    template is missing from ``kwargs``, this function does NOT raise;
    instead it logs a warning (in English) and returns the unformatted
    template as a usable fallback (FR-019b).
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
