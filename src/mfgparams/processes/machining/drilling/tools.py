"""Drilling-specific drill-tool registry (FR-005).

Factors are relative to the HSS baseline (factor 1.0) stored in
``mfgparams.registry``'s material reference values; see research.md #4.
Typical multiplier ranges are drawn from general-purpose machining
references (Machinery's Handbook / Sandvik Coromant): carbide tooling
tolerates substantially higher cutting speeds than HSS, cobalt moderately
higher.

Since ``specs/005-configurable-materials-tools``, the registry is built by
merging the bundled ``processes/machining/drilling/data/tools.toml`` package-data
file with an optional user-supplied override/addition file
(``registry_config.py``), rather than from a hard-coded Python list.
Zero-config (``config_path=None``) behavior is byte-for-byte identical to
the pre-feature hard-coded registry (FR-014, SC-002).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mfgparams.registry_config import (
    RawRegistryEntry,
    load_and_merge,
    require_positive_finite_field,
)

_BUNDLED_PACKAGE = "mfgparams.processes.machining.drilling.data"
_BUNDLED_RESOURCE = "tools.toml"
_TABLE_KEY = "tools"

# TOML key -> dataclass field mapping (data-model.md). Tool factor field
# names are unchanged between the TOML key and the dataclass field.
_FIELD_MAP = {
    "cutting_speed_factor": "cutting_speed_factor",
    "feed_factor": "feed_factor",
}


@dataclass(frozen=True)
class DrillingTool:
    """Reference data for a selectable drill bit type.

    Attributes:
        name: Unique display name, e.g. ``"Carbide"``.
        cutting_speed_factor: Multiplier applied to the material's reference
            cutting speed.
        feed_factor: Multiplier applied to the material's reference feed per
            revolution.
        unit_system: The unit system declared for this entry (``"metric"``
            or ``"imperial"``); accepted, stored, and displayed (FR-011,
            FR-013), but performs no numeric conversion — both factors are
            dimensionless ratios relative to the material's own reference
            values, so they carry no independent physical unit to convert
            (research.md #5). This is an intentional, documented no-op.
        translations: Locale code -> translated display name (FR-009);
            empty by default.
    """

    name: str
    cutting_speed_factor: float
    feed_factor: float
    unit_system: str = "metric"
    translations: dict[str, str] = field(default_factory=dict)

    def display_name(self, locale: str) -> str:
        """Return the translated display name for ``locale``, or English fallback.

        Mirrors ``WorkpieceMaterial.display_name`` (research.md #7).
        """

        return self.translations.get(locale, self.name)


def _to_tool(entry: RawRegistryEntry) -> DrillingTool:
    """Convert a merged :class:`RawRegistryEntry` into a `DrillingTool`.

    No unit conversion is performed regardless of ``entry.unit_system`` —
    ``cutting_speed_factor``/``feed_factor`` are dimensionless (research.md
    #5) — the declared unit system is stored/displayed only.

    Raises:
        RegistryConfigError: If a required factor field is missing,
            non-numeric (including a TOML boolean or a quoted numeric
            string), non-finite, or not positive — via
            :func:`~mfgparams.registry_config.require_positive_finite_field`,
            shared with milling's and turning's own tool converters
            (Constitution Principle VI) rather than re-implemented here.
            The reported path is the entry's own ``source_path`` so a
            user-supplied file is blamed accurately rather than the
            bundled file (FR-007).
    """

    source_path = entry.source_path or _BUNDLED_RESOURCE
    values = {
        dataclass_field: require_positive_finite_field(
            entry.fields, toml_key, source_path=source_path, kind="tool", name=entry.name
        )
        for toml_key, dataclass_field in _FIELD_MAP.items()
    }

    tool = DrillingTool(
        name=entry.name,
        cutting_speed_factor=values["cutting_speed_factor"],
        feed_factor=values["feed_factor"],
        unit_system=entry.unit_system,
        translations=dict(entry.translations),
    )
    return tool


def _build_registry(config_path: str | None) -> dict[str, DrillingTool]:
    result = load_and_merge(_BUNDLED_PACKAGE, _BUNDLED_RESOURCE, config_path, _TABLE_KEY)
    registry: dict[str, DrillingTool] = {}
    for entry in result.entries:
        tool = _to_tool(entry)
        registry[tool.name] = tool
    return registry


# Bundled-only registry, built at import time (zero-config default, FR-014).
TOOL_REGISTRY: dict[str, DrillingTool] = _build_registry(None)


def list_tools(config_path: str | None = None) -> list[str]:
    """Return the currently registered drilling tool names (FR-005).

    Args:
        config_path: Optional path to a user-supplied materials/tools
            configuration file (``contracts/materials-config-schema.md``).
            Defaults to ``None``, which reproduces the bundled-only,
            pre-``005-configurable-materials-tools`` behavior exactly
            (FR-014).
    """

    if config_path is None:
        return list(TOOL_REGISTRY.keys())
    return list(_build_registry(config_path).keys())


def get_tool(name: str, config_path: str | None = None) -> DrillingTool | None:
    """Look up a registered drilling tool by name, or ``None`` if unknown.

    Args:
        name: The tool's canonical English ``name``.
        config_path: Optional path to a user-supplied materials/tools
            configuration file; see :func:`list_tools`.
    """

    if config_path is None:
        return TOOL_REGISTRY.get(name)
    return _build_registry(config_path).get(name)
