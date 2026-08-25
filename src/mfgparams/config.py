"""Shared TOML configuration loading (FR-018; research.md #3, #5).

Configuration overrides the default validation bounds (max diameter/depth).
When the file or a given key is absent, built-in defaults are used.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:  # Python 3.11+ ships tomllib in the standard library.
    import tomllib
except ModuleNotFoundError:  # Python 3.9 / 3.10 fall back to the tomli backport.
    import tomli as tomllib  # type: ignore[no-redef]  # tomli is a drop-in tomllib backport; mypy sees this as an invalid redefinition, but it's the intended fallback for Python <3.11

DEFAULT_MAX_DIAMETER_MM = 100.0
DEFAULT_MAX_DEPTH_MM = 500.0
DEFAULT_MAX_MILL_DIAMETER_MM = 200.0
DEFAULT_MAX_DEPTH_OF_CUT_MM = 50.0
DEFAULT_MAX_LENGTH_OF_CUT_MM = 1000.0


@dataclass(frozen=True)
class Configuration:
    """Effective validation bounds, in canonical metric units.

    Attributes:
        max_diameter_mm: Maximum allowed drill diameter, in mm.
        max_depth_mm: Maximum allowed hole depth, in mm.
        max_mill_diameter_mm: Maximum allowed end-mill/face-mill cutter
            diameter, in mm (specs/009-milling-calculations FR-018).
        max_depth_of_cut_mm: Maximum allowed axial depth of cut and radial
            depth/width of cut, in mm (FR-018).
        max_length_of_cut_mm: Maximum allowed milling length of cut, in mm
            (FR-018).

    The milling bounds are generous sanity limits intended to catch typos
    and unit mistakes, not machining recommendations; they are overridable
    through the same optional TOML file as the drilling bounds
    (specs/009-milling-calculations/research.md #8).
    """

    max_diameter_mm: float = DEFAULT_MAX_DIAMETER_MM
    max_depth_mm: float = DEFAULT_MAX_DEPTH_MM
    max_mill_diameter_mm: float = DEFAULT_MAX_MILL_DIAMETER_MM
    max_depth_of_cut_mm: float = DEFAULT_MAX_DEPTH_OF_CUT_MM
    max_length_of_cut_mm: float = DEFAULT_MAX_LENGTH_OF_CUT_MM


def load_configuration(config_path: str | None = None) -> Configuration:
    """Load a :class:`Configuration` from an optional TOML file.

    Args:
        config_path: Path to a TOML file with optional ``max_diameter_mm``,
            ``max_depth_mm``, ``max_mill_diameter_mm``,
            ``max_depth_of_cut_mm`` and ``max_length_of_cut_mm`` keys — one
            shared file for every operation's bounds, not one file per
            operation (specs/009-milling-calculations FR-018). If ``None``
            or the file does not exist, built-in defaults are used. If the
            file exists but a key is missing, that key's default is used.

    Returns:
        A :class:`Configuration` with the effective bounds.
    """

    if config_path is None:
        return Configuration()

    path = Path(config_path)
    if not path.is_file():
        return Configuration()

    with path.open("rb") as fh:
        data = tomllib.load(fh)

    return Configuration(
        max_diameter_mm=float(data.get("max_diameter_mm", DEFAULT_MAX_DIAMETER_MM)),
        max_depth_mm=float(data.get("max_depth_mm", DEFAULT_MAX_DEPTH_MM)),
        max_mill_diameter_mm=float(data.get("max_mill_diameter_mm", DEFAULT_MAX_MILL_DIAMETER_MM)),
        max_depth_of_cut_mm=float(data.get("max_depth_of_cut_mm", DEFAULT_MAX_DEPTH_OF_CUT_MM)),
        max_length_of_cut_mm=float(data.get("max_length_of_cut_mm", DEFAULT_MAX_LENGTH_OF_CUT_MM)),
    )
