"""Shared workpiece material registry (FR-004).

Reference cutting-speed/feed values are canonical-metric, HSS-baseline
figures drawn from widely published machining data (Machinery's Handbook /
Sandvik Coromant general-purpose reference ranges for twist drilling); see
``specs/001-metal-drilling-calc/research.md`` #4. Drilling-tool factors
(``operations/drilling/tools.py``) multiply these baseline values.

Since ``specs/005-configurable-materials-tools``, the registry is built by
merging the bundled ``data/materials.toml`` package-data file with an
optional user-supplied override/addition file (``registry_config.py``),
rather than from a hard-coded Python list. Zero-config (``config_path=None``)
behavior is byte-for-byte identical to the pre-feature hard-coded registry
(FR-014, SC-002).
"""

from __future__ import annotations

import functools
import logging
import math
import unicodedata
from dataclasses import dataclass, field

from mfgparams.registry_config import RawRegistryEntry, load_and_merge
from mfgparams.units import ft_min_to_m_min, in_to_mm, psi_to_n_per_mm2

_BUNDLED_PACKAGE = "mfgparams.data"
_BUNDLED_RESOURCE = "materials.toml"
_TABLE_KEY = "materials"

#: Fallback category for entries that omit ``material_type`` (008 FR-011).
#: Keeps pre-008 user-supplied config files loadable unchanged.
DEFAULT_MATERIAL_TYPE = "uncategorized"

#: Unicode general categories rejected in a ``material_type`` id: ``Cc``
#: covers the C0 and C1 control ranges (including tab, newline and DEL),
#: ``Zl``/``Zp`` the line and paragraph separators. Everything else --
#: including printable non-ASCII spacing -- is a usable single-line id.
_FORBIDDEN_ID_CATEGORIES = frozenset({"Cc", "Zl", "Zp"})

#: Fields carried over from the bundled entry when a user override omits
#: them (``registry_config.merge_entries``). Without this, a config file
#: written before ``material_type`` existed would silently move the
#: materials it overrides into ``DEFAULT_MATERIAL_TYPE``.
_STICKY_FIELDS = ("material_type",)

# TOML key -> dataclass field mapping (data-model.md "TOML key -> dataclass
# field mapping"). Dataclass field names are never renamed; only this
# parse-time mapping is new.
_FIELD_MAP = {
    "reference_cutting_speed": "reference_cutting_speed_m_min",
    "reference_feed_per_rev": "reference_feed_per_rev_mm",
    "specific_cutting_force": "specific_cutting_force_kc",
}
_REQUIRED_NUMERIC_FIELDS = tuple(_FIELD_MAP.keys())
_CANONICAL_NUMERIC_FIELDS = tuple(_FIELD_MAP.values())

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkpieceMaterial:
    """Reference machining data for a selectable workpiece material.

    Attributes:
        name: Unique display name, e.g. ``"Mild Steel"``.
        material_type: Category identifier grouping this material in the
            two-step (type -> material) selection flow, e.g. ``"metal"`` or
            ``"wood"`` (008 FR-001, FR-005). Free-form rather than a closed
            enum so a new category can be introduced by data alone
            (008 FR-004); defaults to :data:`DEFAULT_MATERIAL_TYPE` when the
            source entry omits the key.
        reference_cutting_speed_m_min: HSS-baseline cutting speed (vc) in
            m/min.
        reference_feed_per_rev_mm: HSS-baseline feed per revolution (fn) in
            mm/rev.
        specific_cutting_force_kc: Specific cutting force (Kc) in N/mm^2,
            used in torque/power calculations.
        unit_system: The unit system the entry was *authored*/declared in
            (``"metric"`` or ``"imperial"``); retained purely for
            display/audit after conversion (FR-011, FR-013) — calculation
            always uses the canonical-metric fields above.
        translations: Locale code -> translated display name (FR-009);
            empty by default.
    """

    name: str
    reference_cutting_speed_m_min: float
    reference_feed_per_rev_mm: float
    specific_cutting_force_kc: float
    unit_system: str = "metric"
    translations: dict[str, str] = field(default_factory=dict)
    material_type: str = DEFAULT_MATERIAL_TYPE

    def display_name(self, locale: str) -> str:
        """Return the translated display name for ``locale``, or English fallback.

        Mirrors ``mfgparams.i18n.translate``'s English-fallback rule
        (research.md #7), but operates on data rather than the message
        catalog.
        """

        return self.translations.get(locale, self.name)

    @property
    def is_usable(self) -> bool:
        """Return ``True`` when all numeric fields are finite and positive.

        Materials with invalid source data are still registered per FR-008
        (warn-and-continue), with invalid fields stored as ``nan``. Check
        this property (or :func:`get_material_validation`) before using the
        numeric fields in a calculation — feeding a non-usable material into
        a formula would silently propagate ``nan``.
        """

        return all(
            math.isfinite(value) and value > 0
            for value in (
                self.reference_cutting_speed_m_min,
                self.reference_feed_per_rev_mm,
                self.specific_cutting_force_kc,
            )
        )


@dataclass(frozen=True)
class MaterialValidationRecord:
    """Load-time validation status for one material entry (FR-008)."""

    material_name: str
    status: str
    issues: tuple[str, ...]
    source_path: str


@dataclass(frozen=True)
class _RegistrySnapshot:
    materials: dict[str, WorkpieceMaterial]
    validation: dict[str, MaterialValidationRecord]


def _warn_validation(record: MaterialValidationRecord) -> None:
    if record.status != "warning":
        return
    _LOGGER.warning(
        "Material entry %r from %s has validation issue(s): %s",
        record.material_name,
        record.source_path,
        "; ".join(record.issues),
    )


def _validate(material: WorkpieceMaterial, source_path: str = _BUNDLED_RESOURCE) -> tuple[str, ...]:
    """Validate ``material``'s numeric fields and return issue details.

    Args:
        source_path: The bundled resource name or user-supplied path this
            material was parsed from (``RawRegistryEntry.source_path``),
            used to report an accurate error location (FR-007) rather than
            always pointing at the bundled file.
    """
    issues: list[str] = []
    if material.reference_cutting_speed_m_min <= 0:
        issues.append("reference_cutting_speed_m_min must be positive")
    if material.reference_feed_per_rev_mm <= 0:
        issues.append("reference_feed_per_rev_mm must be positive")
    if material.specific_cutting_force_kc <= 0:
        issues.append("specific_cutting_force_kc must be positive")
    return tuple(issues)


def _parse_material_type(entry: RawRegistryEntry, issues: list[str]) -> str:
    """Resolve an entry's ``material_type``, appending any issue to ``issues``.

    Follows the registry's established warn-and-continue policy (FR-008): a
    missing key is not an error (it yields :data:`DEFAULT_MATERIAL_TYPE`),
    and a present-but-invalid value is recorded as a validation issue while
    still falling back to the default so the material stays selectable
    (008 FR-011).

    A value is invalid if it is not a non-empty string, or if it contains a
    C0/C1 control character or a Unicode line/paragraph separator. TOML
    multiline strings make the latter reachable
    (``material_type = \"\"\"metal\\nalloy\"\"\"``), and an id containing a
    line break would be offered as a prompt option that ``input()`` can
    never return, making the category and its materials permanently
    unselectable (008 FR-006a). Controls are rejected rather than merely
    line breaks because values such as ``U+009B`` are emitted straight into
    the terminal prompt. Printable non-ASCII spacing (a non-breaking space,
    say) stays valid, so single-line Unicode ids remain usable.
    """

    raw = entry.fields.get("material_type")
    if raw is None:
        return DEFAULT_MATERIAL_TYPE
    if not isinstance(raw, str) or not raw.strip():
        issues.append(f"field 'material_type' must be a non-empty string, got {raw!r}")
        return DEFAULT_MATERIAL_TYPE
    value = raw.strip()
    if any(unicodedata.category(character) in _FORBIDDEN_ID_CATEGORIES for character in value):
        issues.append(
            f"field 'material_type' must be a single line without control "
            f"characters, got {raw!r}"
        )
        return DEFAULT_MATERIAL_TYPE
    return value


def _to_material(entry: RawRegistryEntry) -> tuple[WorkpieceMaterial, MaterialValidationRecord]:
    """Convert a merged :class:`RawRegistryEntry` into a `WorkpieceMaterial`.

    Applies imperial->metric conversion of the three numeric fields when
    ``entry.unit_system == "imperial"`` (FR-012), via ``units.py`` helpers,
    before validation.
    """

    values: dict[str, float] = {}
    issues: list[str] = []
    source_path = entry.source_path or _BUNDLED_RESOURCE
    for toml_key, dataclass_field in _FIELD_MAP.items():
        if toml_key not in entry.fields:
            issues.append(f"missing required field {toml_key!r}")
            values[dataclass_field] = float("nan")
            continue

        raw = entry.fields[toml_key]
        try:
            raw_value = float(raw)
        except (TypeError, ValueError):
            issues.append(f"field {toml_key!r} must be a number, got {raw!r}")
            values[dataclass_field] = float("nan")
            continue
        if not math.isfinite(raw_value):
            issues.append(f"field {toml_key!r} must be finite, got {raw!r}")
            values[dataclass_field] = float("nan")
            continue
        values[dataclass_field] = raw_value

    if entry.unit_system == "imperial":
        speed = values["reference_cutting_speed_m_min"]
        feed = values["reference_feed_per_rev_mm"]
        force = values["specific_cutting_force_kc"]
        values["reference_cutting_speed_m_min"] = (
            ft_min_to_m_min(speed) if math.isfinite(speed) else speed
        )
        values["reference_feed_per_rev_mm"] = in_to_mm(feed) if math.isfinite(feed) else feed
        values["specific_cutting_force_kc"] = (
            psi_to_n_per_mm2(force) if math.isfinite(force) else force
        )

    material = WorkpieceMaterial(
        name=entry.name,
        reference_cutting_speed_m_min=values["reference_cutting_speed_m_min"],
        reference_feed_per_rev_mm=values["reference_feed_per_rev_mm"],
        specific_cutting_force_kc=values["specific_cutting_force_kc"],
        unit_system=entry.unit_system,
        translations=dict(entry.translations),
        material_type=_parse_material_type(entry, issues),
    )
    for field_name in _CANONICAL_NUMERIC_FIELDS:
        value = getattr(material, field_name)
        if math.isfinite(value) and value <= 0:
            issues.append(f"{field_name} must be positive")
    record = MaterialValidationRecord(
        material_name=material.name,
        status="warning" if issues else "valid",
        issues=tuple(issues),
        source_path=source_path,
    )
    return material, record


def _build_registry(config_path: str | None) -> _RegistrySnapshot:
    result = load_and_merge(
        _BUNDLED_PACKAGE, _BUNDLED_RESOURCE, config_path, _TABLE_KEY, _STICKY_FIELDS
    )
    registry: dict[str, WorkpieceMaterial] = {}
    validation: dict[str, MaterialValidationRecord] = {}
    for entry in result.entries:
        material, record = _to_material(entry)
        _warn_validation(record)
        registry[material.name] = material
        validation[material.name] = record
    return _RegistrySnapshot(materials=registry, validation=validation)


@functools.cache
def _build_registry_cached(config_path: str) -> _RegistrySnapshot:
    return _build_registry(config_path)


# Bundled-only registry, built at import time (zero-config default, FR-014).
_BUNDLED_SNAPSHOT = _build_registry(None)
MATERIAL_REGISTRY: dict[str, WorkpieceMaterial] = _BUNDLED_SNAPSHOT.materials


def _snapshot_for(config_path: str | None) -> _RegistrySnapshot:
    if config_path is None:
        return _BUNDLED_SNAPSHOT
    return _build_registry_cached(config_path)


def list_materials(config_path: str | None = None, material_type: str | None = None) -> list[str]:
    """Return the currently registered workpiece material names (FR-004).

    Args:
        config_path: Optional path to a user-supplied materials/tools
            configuration file (``contracts/materials-config-schema.md``).
            Defaults to ``None``, which reproduces the bundled-only,
            pre-``005-configurable-materials-tools`` behavior exactly
            (FR-014).
        material_type: Optional category filter (008 FR-002), e.g.
            ``"metal"``. ``None`` (the default) returns every material in
            registration order, preserving the pre-008 signature and
            behavior. An unknown category yields an empty list rather than
            raising, so a stale selection degrades gracefully (008 FR-011).
    """

    if config_path is None:
        materials = MATERIAL_REGISTRY
    else:
        materials = _snapshot_for(config_path).materials
    if material_type is None:
        return list(materials.keys())
    return [name for name, material in materials.items() if material.material_type == material_type]


def materials_load_notice(
    config_path: str | None = None,
) -> tuple[str | None, tuple[tuple[str, object], ...]]:
    """Return the non-fatal load notice for the materials registry, if any.

    Exists so callers never have to re-specify the bundled resource
    coordinates or the sticky-field tuple themselves. Passing a different
    ``sticky_fields`` value produces a different ``load_and_merge`` cache
    key, which would silently reread and reparse both TOML files instead of
    reusing the load the registry already performed.

    Args:
        config_path: Optional path to a user-supplied materials TOML file.

    Returns:
        A ``(notice_key, notice_kwargs)`` pair; ``notice_key`` is ``None``
        when the load produced no notice.
    """

    result = load_and_merge(
        _BUNDLED_PACKAGE, _BUNDLED_RESOURCE, config_path, _TABLE_KEY, _STICKY_FIELDS
    )
    return result.notice_key, result.notice_kwargs


def list_material_types(config_path: str | None = None) -> list[str]:
    """Return the registered material-type identifiers (008 FR-001, FR-006).

    Types are derived from the effective material set rather than from a
    separate hard-coded list, so declaring a new ``material_type`` in a
    bundled or user-supplied config file registers a new category with no
    code change (008 FR-004). Order follows each type's first appearance in
    registration order, which makes the display order configurable by
    ordering entries in the TOML file (008 FR-010).

    Args:
        config_path: Optional path to a user-supplied materials/tools
            configuration file; see :func:`list_materials`.
    """

    if config_path is None:
        materials = MATERIAL_REGISTRY
    else:
        materials = _snapshot_for(config_path).materials
    # dict preserves insertion order, giving first-appearance ordering
    # without a second pass or an explicit `seen` set.
    return list(dict.fromkeys(material.material_type for material in materials.values()))


def get_material(name: str, config_path: str | None = None) -> WorkpieceMaterial | None:
    """Look up a registered material by name, or ``None`` if unknown.

    Args:
        name: The material's canonical English ``name``.
        config_path: Optional path to a user-supplied materials/tools
            configuration file; see :func:`list_materials`.

    Warning:
        Entries with invalid source data are still registered per FR-008
        (warn-and-continue) and may carry ``nan`` numeric fields. Check
        :attr:`WorkpieceMaterial.is_usable` (or
        :func:`get_material_validation`) before using the returned
        material's numeric fields in a calculation.
    """

    return _snapshot_for(config_path).materials.get(name)


def get_material_validation(
    name: str, config_path: str | None = None
) -> MaterialValidationRecord | None:
    """Return load-time validation record for ``name`` (FR-008)."""

    return _snapshot_for(config_path).validation.get(name)
