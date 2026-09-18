"""Shared data-shaping helpers for the text GUI's operation screens.

Ports `console/cli.py`'s REPL-independent data-shaping logic (label
building, collision-safe reverse lookups, error/result rendering)
unchanged (research.md #3). 018-tui-splitpane-redesign's instant-edit split
pane (`screens/split_pane.py`) replaced this module's old dialog-prompt
functions (`ask_*`, `show_result`, the `Cancelled` sentinel) — those existed
to drive `prompt_toolkit.shortcuts`' modal dialogs one field at a time, with
an explicit Back/Cancel action to defer a partial commit; the split pane
commits every field immediately as it's edited (FR-016) and has no
per-field Back/Cancel step for a cancel sentinel to distinguish (research.md
consolidated decisions table). Only the still-relevant pure functions
remain: unit conversion, error/result rendering, and label building, reused
by both `screens/drilling.py` and `screens/milling.py` (Constitution
Principle I).
"""

from __future__ import annotations

from collections import Counter

from mfgparams import UnitSystem
from mfgparams.console.i18n import DEFAULT_LOCALE, has_message, translate
from mfgparams.models import CalculationMode, ErrorInfo
from mfgparams.processes.machining.drilling.tools import DrillingTool
from mfgparams.processes.machining.milling._tool_registry import MillingTool
from mfgparams.processes.machining.turning.tools import TurningTool
from mfgparams.registry import WorkpieceMaterial
from mfgparams.units import hp_to_kw, in_to_mm, kw_to_hp, mm_to_in

UNIT_LABELS = {
    UnitSystem.METRIC: {
        "diameter": "mm",
        "depth": "mm",
        "feed_rate": "mm/min",
        "torque": "N·m",
        "power": "kW",
        "feed_per_tooth": "mm/tooth",
        "material_removal_rate": "cm³/min",
        "depth_of_cut": "mm",
        "cutting_force": "N",
        "feed_per_rotation": "mm/rev",
    },
    UnitSystem.IMPERIAL: {
        "diameter": "in",
        "depth": "in",
        "feed_rate": "in/min",
        "torque": "in-lb",
        "power": "HP",
        "feed_per_tooth": "in/tooth",
        "material_removal_rate": "in³/min",
        "depth_of_cut": "in",
        "cutting_force": "lbf",
        "feed_per_rotation": "in/rev",
    },
}


def convert_length(value: float, from_system: UnitSystem, to_system: UnitSystem) -> float:
    """Convert a stored length/feed-per-tooth value between unit systems.

    Used when the unit-system field changes mid-session, so a remembered
    value keeps its physical meaning instead of being re-offered as-is
    under the new unit's label (e.g. a remembered 10 mm silently becoming a
    defaulted "10 in").
    """

    if from_system is to_system:
        return value
    return mm_to_in(value) if to_system is UnitSystem.IMPERIAL else in_to_mm(value)


def convert_power(value: float, from_system: UnitSystem, to_system: UnitSystem) -> float:
    """Convert a stored power value between unit systems (kW<->HP). See
    `convert_length` for why this conversion is needed at all."""

    if from_system is to_system:
        return value
    return kw_to_hp(value) if to_system is UnitSystem.IMPERIAL else hp_to_kw(value)


def render_error(error: ErrorInfo, locale: str) -> str:
    """Render an :class:`ErrorInfo` for display, translating it if needed.

    Ported unchanged from `console/cli.py`'s `_render_error` (research.md #3)
    -- see that function's original docstring for the full rationale; the
    logic (not just the shape) is identical, only the caller changed.
    """

    if locale == DEFAULT_LOCALE or not has_message(locale, error.message_key):
        return error.message

    kwargs = dict(error.kwargs)
    label_key = kwargs.pop("label_key", None)
    if isinstance(label_key, str) and has_message(locale, label_key):
        kwargs["label"] = translate(locale, label_key)
    return translate(locale, error.message_key, **kwargs)


def display_label(
    entry: WorkpieceMaterial | DrillingTool | MillingTool | TurningTool,
    display_locale: str,
    message_locale: str,
) -> str:
    """Build a material/tool display label. Ported unchanged from
    `console/cli.py`'s `_display_label` (research.md #3)."""

    name = entry.display_name(display_locale)
    if entry.unit_system == "metric":
        return name
    return translate(
        message_locale, "tui.label.unit_system_suffix", name=name, unit_system=entry.unit_system
    )


def material_type_label(material_type: str, locale: str) -> str:
    """Ported unchanged from `console/cli.py`'s `_material_type_label`."""

    key = f"material_type.{material_type}"
    if has_message(locale, key):
        return translate(locale, key)
    fallback = material_type.replace("_", " ").replace("-", " ").title().strip()
    return fallback or material_type


def unique_labels(candidates: dict[str, str]) -> dict[str, str]:
    """Ported unchanged from `console/cli.py`'s `_unique_labels`."""

    collisions = Counter(candidates.values())
    taken: set[str] = set()
    unique: dict[str, str] = {}
    for key, label in candidates.items():
        candidate = f"{label} ({key})" if collisions[label] > 1 else label
        if candidate in taken:
            discriminator = 2
            while f"{candidate} #{discriminator}" in taken:
                discriminator += 1
            candidate = f"{candidate} #{discriminator}"
        taken.add(candidate)
        unique[key] = candidate
    return unique


_SPINDLE_SPEED_MODE_LABEL_KEYS = {
    CalculationMode.STANDARD: "tui.result.spindle_speed.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "tui.result.spindle_speed.mode.power_constrained",
    CalculationMode.FIXED_RPM: "tui.result.spindle_speed.mode.fixed_rpm",
    # specs/020-turning-feed-per-rotation research.md #9: this dict is a
    # hard lookup (not a .get() with a fallback) -- an unhandled
    # CalculationMode member here raises KeyError for every result in that
    # mode, so this entry is required, not optional polish.
    CalculationMode.FEED_RATE_CONSTRAINED: "tui.result.spindle_speed.mode.feed_rate_constrained",
}


def format_result(result, labels: dict[str, str], locale: str) -> str:
    """Render a `CalculationResult` as display text. Ports `console/cli.py`'s
    `_display_result` (research.md #3), returning a string for the right
    pane instead of `print()`-ing line by line."""

    if result.error is not None:
        return render_error(result.error, locale)

    mode_label = translate(locale, _SPINDLE_SPEED_MODE_LABEL_KEYS[result.mode])
    mode_suffix = translate(locale, "tui.result.spindle_speed.mode_suffix", label=mode_label)
    lines = [
        translate(
            locale,
            "tui.result.spindle_speed",
            value=f"{result.spindle_speed_rpm:.1f}",
            mode_suffix=mode_suffix,
        ),
        translate(
            locale,
            "tui.result.feed_rate",
            value=f"{result.feed_rate:.1f}",
            unit=labels["feed_rate"],
        ),
    ]
    if result.feed_per_rotation is not None:
        lines.append(
            translate(
                locale,
                "tui.result.feed_per_rotation",
                value=f"{result.feed_per_rotation:.4g}",
                unit=labels["feed_per_rotation"],
            )
        )
    lines += [
        translate(locale, "tui.result.machining_time", value=f"{result.machining_time:.2f}"),
        translate(locale, "tui.result.torque", value=f"{result.torque:.1f}", unit=labels["torque"]),
        translate(
            locale,
            "tui.result.power_required",
            value=f"{result.power_required:.2f}",
            unit=labels["power"],
        ),
    ]
    if result.material_removal_rate is not None:
        lines.append(
            translate(
                locale,
                "tui.result.material_removal_rate",
                value=f"{result.material_removal_rate:.2f}",
                unit=labels["material_removal_rate"],
            )
        )
    if result.cutting_force is not None:
        lines.append(
            translate(
                locale,
                "tui.result.cutting_force",
                value=f"{result.cutting_force:.1f}",
                unit=labels["cutting_force"],
            )
        )
    text = "\n".join(lines)
    if result.feasibility_warning:
        text += translate(locale, "tui.result.warning", message=result.feasibility_warning)
    return text
