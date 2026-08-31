"""Shared, kind-agnostic materials/tools configuration parsing and merging.

Implements the TOML parse / fallback / duplicate-detection / merge logic
described in ``specs/005-configurable-materials-tools/data-model.md``
("Merge Algorithm") and ``research.md`` #1, #2, #4, #6, #9. Reused by both
``mfgparams.registry`` (materials) and
``mfgparams.processes.machining.drilling.tools`` (tools) so that any future
operation-specific registry can reuse this module unchanged (Constitution
Principle VI).

This module is intentionally dataclass-agnostic: it produces plain
``RawRegistryEntry`` objects, not ``WorkpieceMaterial``/``DrillingTool``
instances. Unit conversion and dataclass construction remain the
responsibility of the per-kind callers (FR-006, FR-017).
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

try:  # Python 3.11+ ships tomllib in the standard library.
    import tomllib
except ModuleNotFoundError:  # Python 3.9 / 3.10 fall back to the tomli backport.
    import tomli as tomllib  # type: ignore[no-redef]  # tomli is a drop-in tomllib backport; mypy sees this as an invalid redefinition, but it's the intended fallback for Python <3.11

_VALID_UNIT_SYSTEMS = ("metric", "imperial")


class RegistryConfigError(Exception):
    """Raised when a user-supplied materials/tools file cannot be safely applied.

    Never raised for a merely missing/unreadable file (see
    :func:`load_and_merge`'s ``notice_key`` return value instead).

    Attributes:
        message_key: Message-catalog key (Constitution Principle VIII), e.g.
            ``"error.materials_config.malformed"``.
        kwargs: ``str.format()`` placeholder values for the catalog message
            (e.g. ``path``, ``name``, ``kind``, ``details``).
    """

    def __init__(self, message_key: str, **kwargs: object) -> None:
        self.message_key = message_key
        self.kwargs = kwargs
        super().__init__(message_key)


@dataclass(frozen=True)
class RawRegistryEntry:
    """Parse-time, kind-agnostic intermediate representation of one entry.

    Attributes:
        name: Unique display name/identifier within the merged set for its
            kind (FR-006, FR-016).
        fields: The kind-specific numeric reference fields, still in their
            *declared* unit system (data-model.md "TOML key -> dataclass
            field mapping").
        unit_system: ``"metric"`` or ``"imperial"``; defaults to
            ``"metric"`` when the TOML entry omits the key (FR-011).
        translations: Locale code -> translated display name; may be empty.
        source_path: The bundled resource name or user-supplied path this
            entry was parsed from (or, after an override merge, the user
            path that replaced it). Used by callers (``registry.py``/
            ``tools.py``) to report accurate ``RegistryConfigError``
            locations instead of always pointing at the bundled file.
    """

    name: str
    fields: dict[str, Any]
    unit_system: str = "metric"
    translations: dict[str, str] = field(default_factory=dict)
    source_path: str = ""


def _parse_entries(data: dict[str, Any], table_key: str, path: str) -> list[RawRegistryEntry]:
    """Parse the ``[[materials]]``/``[[tools]]`` array-of-tables into entries."""

    raw_entries = data.get(table_key, [])
    entries: list[RawRegistryEntry] = []
    for raw in raw_entries:
        name = raw.get("name")
        if not name:
            raise RegistryConfigError(
                "error.materials_config.invalid_entry",
                path=path,
                kind=table_key[:-1],
                name=name or "",
                details="missing required 'name' field",
            )
        unit_system = raw.get("unit_system", "metric")
        if unit_system not in _VALID_UNIT_SYSTEMS:
            raise RegistryConfigError(
                "error.materials_config.invalid_entry",
                path=path,
                kind=table_key[:-1],
                name=name,
                details=(
                    f"unit_system must be one of {_VALID_UNIT_SYSTEMS!r}, got {unit_system!r}"
                ),
            )
        translations = dict(raw.get("translations", {}))
        fields_dict = {
            key: value
            for key, value in raw.items()
            if key not in ("name", "unit_system", "translations")
        }
        entries.append(
            RawRegistryEntry(
                name=name,
                fields=fields_dict,
                unit_system=unit_system,
                translations=translations,
                source_path=path,
            )
        )
    return entries


def _check_duplicates(entries: list[RawRegistryEntry], kind: str, path: str) -> None:
    """Raise if ``entries`` (a single file's own list) has a duplicate name (FR-016)."""

    seen: set[str] = set()
    for entry in entries:
        if entry.name in seen:
            raise RegistryConfigError(
                "error.materials_config.duplicate_entry",
                path=path,
                kind=kind,
                name=entry.name,
            )
        seen.add(entry.name)


def parse_toml_entries(toml_text: str, table_key: str, path: str) -> list[RawRegistryEntry]:
    """Parse ``toml_text`` into a list of :class:`RawRegistryEntry` for ``table_key``.

    Raises:
        RegistryConfigError: If ``toml_text`` is not valid TOML
            (``error.materials_config.malformed``) or an entry is invalid
            (``error.materials_config.invalid_entry``).
    """

    try:
        data = tomllib.loads(toml_text)
    except tomllib.TOMLDecodeError as exc:
        raise RegistryConfigError(
            "error.materials_config.malformed", path=path, details=str(exc)
        ) from exc

    return _parse_entries(data, table_key, path)


def merge_entries(
    bundled: list[RawRegistryEntry],
    user: list[RawRegistryEntry] | None,
    sticky_fields: tuple[str, ...] = (),
) -> list[RawRegistryEntry]:
    """Merge ``user`` entries into ``bundled`` by name (data-model.md "Merge Algorithm").

    A ``user`` entry whose name matches a ``bundled`` entry replaces that
    entry's ``fields``/``unit_system`` wholesale and merges ``translations``
    per-locale (user's locale value wins for that locale only). A ``user``
    entry with a new name is appended. ``bundled`` entries untouched by
    ``user`` are returned unchanged, in original order, followed by any
    newly-appended entries in ``user`` order.

    Args:
        sticky_fields: Field keys exempted from the wholesale-replace rule:
            if the user entry omits such a key, the bundled entry's value is
            carried over instead of being dropped. Used for classification
            metadata rather than reference values — ``material_type``
            (specs/008-material-categorization) — so that a config file
            written before that key existed keeps its materials in their
            original categories instead of silently falling back to
            ``"uncategorized"``.
    """

    if not user:
        return list(bundled)

    merged_by_name: dict[str, RawRegistryEntry] = {entry.name: entry for entry in bundled}
    order: list[str] = [entry.name for entry in bundled]

    for user_entry in user:
        existing = merged_by_name.get(user_entry.name)
        if existing is None:
            order.append(user_entry.name)
            merged_by_name[user_entry.name] = user_entry
            continue

        merged_translations = dict(existing.translations)
        merged_translations.update(user_entry.translations)
        merged_fields = dict(user_entry.fields)
        for key in sticky_fields:
            if key not in merged_fields and key in existing.fields:
                merged_fields[key] = existing.fields[key]
        merged_by_name[user_entry.name] = RawRegistryEntry(
            name=user_entry.name,
            fields=merged_fields,
            unit_system=user_entry.unit_system,
            translations=merged_translations,
            source_path=user_entry.source_path,
        )

    return [merged_by_name[name] for name in order]


@dataclass(frozen=True)
class MergeResult:
    """Result of :func:`load_and_merge`.

    Attributes:
        entries: The merged, kind-agnostic effective entry list.
        notice_key: A message-catalog key to surface to the caller (e.g.
            ``"notice.materials_config.not_found"``) if the user-supplied
            path was given but missing/unreadable, else ``None``.
        notice_kwargs: ``str.format()`` kwargs for ``notice_key``.
    """

    entries: tuple[RawRegistryEntry, ...]
    notice_key: str | None = None
    notice_kwargs: tuple[tuple[str, object], ...] = ()


def _read_user_file(user_path: str | None) -> str | None:
    if user_path is None:
        return None
    path = Path(user_path)
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _load_and_merge_uncached(
    bundled_package: str,
    bundled_resource: str,
    user_path: str | None,
    table_key: str,
    sticky_fields: tuple[str, ...] = (),
) -> MergeResult:
    bundled_text = (
        resources.files(bundled_package).joinpath(bundled_resource).read_text(encoding="utf-8")
    )
    bundled_entries = parse_toml_entries(bundled_text, table_key, bundled_resource)
    kind = table_key[:-1]
    _check_duplicates(bundled_entries, kind, bundled_resource)

    if user_path is None:
        return MergeResult(entries=tuple(bundled_entries))

    user_text = _read_user_file(user_path)
    if user_text is None:
        return MergeResult(
            entries=tuple(bundled_entries),
            notice_key="notice.materials_config.not_found",
            notice_kwargs=(("path", user_path),),
        )

    user_entries = parse_toml_entries(user_text, table_key, user_path)
    _check_duplicates(user_entries, kind, user_path)

    merged = merge_entries(bundled_entries, user_entries, sticky_fields)
    return MergeResult(entries=tuple(merged))


@functools.cache
def _load_and_merge_cached(
    bundled_package: str,
    bundled_resource: str,
    user_path: str | None,
    table_key: str,
    sticky_fields: tuple[str, ...] = (),
) -> MergeResult:
    return _load_and_merge_uncached(
        bundled_package, bundled_resource, user_path, table_key, sticky_fields
    )


def load_and_merge(
    bundled_package: str,
    bundled_resource: str,
    user_path: str | None,
    table_key: str,
    sticky_fields: tuple[str, ...] = (),
) -> MergeResult:
    """Load, merge, and cache the effective (bundled + user) entry list.

    Args:
        bundled_package: The package name to read the bundled resource from
            (e.g. ``"mfgparams.data"``), via ``importlib.resources``.
        bundled_resource: The bundled TOML filename within that package
            (e.g. ``"materials.toml"``).
        user_path: Optional path to a user-supplied override/addition file
            (``--materials-config PATH`` or a caller-supplied
            ``config_path``). ``None``, a missing path, or an unreadable
            file all fall back to bundled-only (FR-005) with a notice key.
        table_key: The TOML array-of-tables key to parse (``"materials"`` or
            ``"tools"``).
        sticky_fields: Field keys preserved from the bundled entry when a
            user override omits them; see :func:`merge_entries`.

    Returns:
        A :class:`MergeResult` with the merged entries and an optional
        notice key.

    Raises:
        RegistryConfigError: If the bundled or user file fails to parse, has
            a duplicate name within itself, or contains an invalid entry
            (FR-006, FR-007, FR-016).
    """

    return _load_and_merge_cached(
        bundled_package, bundled_resource, user_path, table_key, sticky_fields
    )


def clear_cache() -> None:
    """Clear the merge-result cache (test support only)."""

    _load_and_merge_cached.cache_clear()
