"""Message catalogs owned by the console, one pure-Python module per locale.

Mirrors :mod:`mfgparams.locales`'s shape exactly (each sibling module exposes
a module-level ``MESSAGES: dict[str, str]``), but a separate package: this
catalog holds UI strings (prompts, labels, status/progress text) the console
displays, while :mod:`mfgparams.locales` keeps only the entries that must
remain reachable without the ``console`` extra installed — error text
(``error.*``/``warning.*``/``notice.*``) and the console-unavailable message
(``console.missing_dependency*``) — per
specs/015-console-i18n-relocation/contracts/catalogue-ownership-contract.md.

A key lives in exactly one of the two catalogs, never both (FR-004): moving
an entry here removes it from :mod:`mfgparams.locales` in the same change.

This feature ships only :mod:`mfgparams.console.locales.en`; additional
languages can be added later by contributing a new sibling module of the
same shape, without any code changes elsewhere.
"""

from __future__ import annotations
