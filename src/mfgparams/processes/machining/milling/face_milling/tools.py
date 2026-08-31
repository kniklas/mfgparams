"""Face-mill tool registry (specs/009-milling-calculations FR-006, FR-015).

Structurally identical to
:mod:`mfgparams.processes.machining.milling.end_milling.tools`, over its own
bundled table (``processes/machining/milling/face_milling/data/tools.toml``) and its
own TOML table key ``face_mill_tools`` — distinct from both drilling's
``tools`` and end milling's ``end_mill_tools`` so that a user configuration
file can extend any one tool kind without affecting the others
(contracts/milling-tools-config-schema.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from mfgparams.processes.machining.milling._tool_registry import MillingTool, build_registry

_BUNDLED_PACKAGE = "mfgparams.processes.machining.milling.face_milling.data"
_BUNDLED_RESOURCE = "tools.toml"
_TABLE_KEY = "face_mill_tools"


@dataclass(frozen=True)
class FaceMillTool(MillingTool):
    """Reference data for a selectable face-mill (facing cutter) type.

    Adds no fields to :class:`~mfgparams.processes.machining.milling._tool_registry.MillingTool`;
    it exists as a distinct type so end-mill and face-mill registries remain
    independently evolvable (research.md #3).
    """


def _build_registry(config_path: str | None) -> dict[str, FaceMillTool]:
    return build_registry(
        FaceMillTool, _BUNDLED_PACKAGE, _BUNDLED_RESOURCE, _TABLE_KEY, config_path
    )


# Bundled-only registry, built at import time (zero-config default).
FACE_MILL_TOOL_REGISTRY: dict[str, FaceMillTool] = _build_registry(None)


def list_face_mill_tools(config_path: str | None = None) -> list[str]:
    """Return the currently registered face-mill tool names (FR-006).

    Args:
        config_path: Optional path to a user-supplied materials/tools
            configuration file (contracts/milling-tools-config-schema.md).
            Defaults to ``None``, which uses the bundled data only.
    """

    if config_path is None:
        return list(FACE_MILL_TOOL_REGISTRY.keys())
    return list(_build_registry(config_path).keys())


def get_face_mill_tool(name: str, config_path: str | None = None) -> FaceMillTool | None:
    """Look up a registered face-mill tool by name, or ``None`` if unknown.

    Args:
        name: The tool's canonical English ``name``.
        config_path: Optional path to a user-supplied configuration file;
            see :func:`list_face_mill_tools`.
    """

    if config_path is None:
        return FACE_MILL_TOOL_REGISTRY.get(name)
    return _build_registry(config_path).get(name)
