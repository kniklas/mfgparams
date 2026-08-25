"""Message catalogs, one pure-Python module per supported locale (FR-019a).

Each sibling module (e.g. ``en``) exposes a module-level ``MESSAGES: dict[str,
str]`` mapping a stable, language-independent message ID to a localized
string. Strings MAY contain ``str.format()``-style named placeholders (e.g.
``"{material}"``) for dynamic values, populated by the caller at lookup time
via :func:`mfgparams.i18n.translate`.

This feature ships only :mod:`mfgparams.locales.en` (FR-019e); additional
languages can be added later by contributing a new sibling module of the
same shape, without any code changes elsewhere (SC-007).
"""

from __future__ import annotations
