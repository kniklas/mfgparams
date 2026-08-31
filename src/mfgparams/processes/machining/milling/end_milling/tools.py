"""End-mill tool registry (specs/009-milling-calculations FR-004, FR-015).

Structurally mirrors ``processes/machining/drilling/tools.py``: the registry is built
by merging the bundled ``processes/machining/milling/end_milling/data/tools.toml``
package-data file with an optional user-supplied override/addition file via
the shared :mod:`mfgparams.registry_config` helper. The parsing and
validation itself lives in :mod:`mfgparams.processes.machining.milling._tool_registry`
so it is not duplicated between the two milling sub-operations.

This registry reads the ``end_mill_tools`` TOML table key, **not** drilling's
``tools`` key: sharing a key would merge end-mill entries into the drilling
registry, where the mandatory ``feed_factor`` field is absent, and would
break the existing drilling flow with a ``RegistryConfigError``
(FR-002, SC-005; contracts/milling-tools-config-schema.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from mfgparams.processes.machining.milling._tool_registry import MillingTool, build_registry

_BUNDLED_PACKAGE = "mfgparams.processes.machining.milling.end_milling.data"
_BUNDLED_RESOURCE = "tools.toml"
_TABLE_KEY = "end_mill_tools"


@dataclass(frozen=True)
class EndMillTool(MillingTool):
    """Reference data for a selectable end-mill type.

    Adds no fields to :class:`~mfgparams.processes.machining.milling._tool_registry.MillingTool`;
    it exists as a distinct type so end-mill and face-mill registries remain
    independently evolvable (research.md #3).
    """


def _build_registry(config_path: str | None) -> dict[str, EndMillTool]:
    return build_registry(EndMillTool, _BUNDLED_PACKAGE, _BUNDLED_RESOURCE, _TABLE_KEY, config_path)


# Bundled-only registry, built at import time (zero-config default).
END_MILL_TOOL_REGISTRY: dict[str, EndMillTool] = _build_registry(None)


def list_end_mill_tools(config_path: str | None = None) -> list[str]:
    """Return the currently registered end-mill tool names (FR-004).

    Args:
        config_path: Optional path to a user-supplied materials/tools
            configuration file (contracts/milling-tools-config-schema.md).
            Defaults to ``None``, which uses the bundled data only.
    """

    if config_path is None:
        return list(END_MILL_TOOL_REGISTRY.keys())
    return list(_build_registry(config_path).keys())


def get_end_mill_tool(name: str, config_path: str | None = None) -> EndMillTool | None:
    """Look up a registered end-mill tool by name, or ``None`` if unknown.

    Args:
        name: The tool's canonical English ``name``.
        config_path: Optional path to a user-supplied configuration file;
            see :func:`list_end_mill_tools`.
    """

    if config_path is None:
        return END_MILL_TOOL_REGISTRY.get(name)
    return _build_registry(config_path).get(name)
