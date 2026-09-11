"""Turning-specific single-point-tool registry (specs/019-turning-calculations FR-005).

Factors are relative to the HSS baseline (factor 1.0) stored in
``mfgparams.registry``'s material reference values; see research.md #1 and
#5. Mirrors ``drilling/tools.py`` exactly (turning is a single-subtype
process, structurally identical to drilling) except for the bundled
resource location and the ``turning_tools`` table key
(contracts/turning-tools-config-schema.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mfgparams.registry_config import (
    RawRegistryEntry,
    load_and_merge,
    require_positive_finite_field,
)

_BUNDLED_PACKAGE = "mfgparams.processes.machining.turning.data"
_BUNDLED_RESOURCE = "tools.toml"
_TABLE_KEY = "turning_tools"

# TOML key -> dataclass field mapping (data-model.md). Tool factor field
# names are unchanged between the TOML key and the dataclass field.
_FIELD_MAP = {
    "cutting_speed_factor": "cutting_speed_factor",
    "feed_factor": "feed_factor",
}

#: Both factor fields are "optional when overriding" per
#: contracts/turning-tools-config-schema.md — an override entry that omits
#: one keeps the bundled entry's value instead of being rejected as missing
#: (mirrors milling's `_tool_registry._STICKY_FIELDS`, which makes the
#: identical promise for its own `cutting_speed_factor`). Without this, a
#: config supplying only `name` + one factor would have that promise broken
#: by `merge_entries()`'s wholesale-replace default (registry_config.py).
_STICKY_FIELDS = ("cutting_speed_factor", "feed_factor")


@dataclass(frozen=True)
class TurningTool:
    """Reference data for a selectable single-point turning tool type.

    Attributes:
        name: Unique display name, e.g. ``"Carbide"``.
        cutting_speed_factor: Multiplier applied to the material's reference
            cutting speed.
        feed_factor: Multiplier applied to the material's reference feed per
            revolution.
        unit_system: The unit system declared for this entry (``"metric"``
            or ``"imperial"``); accepted, stored, and displayed, but
            performs no numeric conversion — both factors are dimensionless
            ratios, so they carry no independent physical unit to convert
            (mirrors ``DrillingTool``'s identical documented no-op).
        translations: Locale code -> translated display name; empty by
            default.
    """

    name: str
    cutting_speed_factor: float
    feed_factor: float
    unit_system: str = "metric"
    translations: dict[str, str] = field(default_factory=dict)

    def display_name(self, locale: str) -> str:
        """Return the translated display name for ``locale``, or English fallback."""

        return self.translations.get(locale, self.name)


def _to_tool(entry: RawRegistryEntry) -> TurningTool:
    """Convert a merged :class:`RawRegistryEntry` into a `TurningTool`.

    Raises:
        RegistryConfigError: If a required factor field is missing,
            non-numeric (including a TOML boolean or a quoted numeric
            string), non-finite, or not positive — via
            :func:`~mfgparams.registry_config.require_positive_finite_field`,
            shared with drilling's and milling's own tool converters
            (Constitution Principle VI) rather than re-implemented here.
    """

    source_path = entry.source_path or _BUNDLED_RESOURCE
    values = {
        dataclass_field: require_positive_finite_field(
            entry.fields, toml_key, source_path=source_path, kind="tool", name=entry.name
        )
        for toml_key, dataclass_field in _FIELD_MAP.items()
    }

    return TurningTool(
        name=entry.name,
        cutting_speed_factor=values["cutting_speed_factor"],
        feed_factor=values["feed_factor"],
        unit_system=entry.unit_system,
        translations=dict(entry.translations),
    )


def _build_registry(config_path: str | None) -> dict[str, TurningTool]:
    result = load_and_merge(
        _BUNDLED_PACKAGE, _BUNDLED_RESOURCE, config_path, _TABLE_KEY, _STICKY_FIELDS
    )
    registry: dict[str, TurningTool] = {}
    for entry in result.entries:
        tool = _to_tool(entry)
        registry[tool.name] = tool
    return registry


# Bundled-only registry, built at import time (zero-config default).
TOOL_REGISTRY: dict[str, TurningTool] = _build_registry(None)


def list_turning_tools(config_path: str | None = None) -> list[str]:
    """Return the currently registered turning tool names (FR-005).

    Args:
        config_path: Optional path to a user-supplied materials/tools
            configuration file
            (contracts/turning-tools-config-schema.md). Defaults to
            ``None``, which returns only the bundled tools.
    """

    if config_path is None:
        return list(TOOL_REGISTRY.keys())
    return list(_build_registry(config_path).keys())


def get_turning_tool(name: str, config_path: str | None = None) -> TurningTool | None:
    """Look up a registered turning tool by name, or ``None`` if unknown.

    Args:
        name: The tool's canonical English ``name``.
        config_path: Optional path to a user-supplied materials/tools
            configuration file; see :func:`list_turning_tools`.
    """

    if config_path is None:
        return TOOL_REGISTRY.get(name)
    return _build_registry(config_path).get(name)
