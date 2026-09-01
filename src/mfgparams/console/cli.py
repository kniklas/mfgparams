"""Interactive text interface (REPL) for drilling calculations (FR-002).

Built strictly on top of the public library API (contracts/cli-repl.md) —
contains no calculation logic of its own; every result comes from
``mfgparams.calculate()``.

All prompts, labels, and messages are sourced from the message catalog via
``mfgparams.i18n`` (FR-019a-c) rather than hard-coded literal strings.
The active locale is resolved exactly once at startup from
``MFGPARAMS_LOCALE`` (:func:`mfgparams.i18n.get_locale`) and held
fixed for the entire REPL loop — it is never re-read mid-session.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter
from dataclasses import dataclass
from typing import Callable, cast

from mfgparams import (
    CalculationMode,
    MachiningOperation,
    MillingSubOperation,
    UnitSystem,
    calculate,
    calculate_end_milling,
    calculate_face_milling,
    list_end_mill_tools,
    list_face_mill_tools,
    list_material_types,
    list_materials,
    list_tools,
)
from mfgparams.config import Configuration
from mfgparams.i18n import get_locale, get_raw_locale, has_message, translate
from mfgparams.logging_setup import configure_logging
from mfgparams.models import ErrorInfo
from mfgparams.processes.machining.drilling.tools import DrillingTool, get_tool
from mfgparams.processes.machining.milling._tool_registry import MillingTool
from mfgparams.processes.machining.milling.end_milling.tools import get_end_mill_tool
from mfgparams.processes.machining.milling.face_milling.tools import get_face_mill_tool
from mfgparams.registry import WorkpieceMaterial, get_material, materials_load_notice
from mfgparams.registry_config import RegistryConfigError
from mfgparams.units import in_to_mm
from mfgparams.validation import (
    validate_depth_mm,
    validate_depth_of_cut_mm,
    validate_diameter_mm,
    validate_engagement_mm,
    validate_feed_per_tooth_mm,
    validate_length_of_cut_mm,
    validate_mill_diameter_mm,
    validate_tooth_count,
)

_DEFAULT_CONFIG = Configuration()

UNIT_LABELS = {
    UnitSystem.METRIC: {
        "diameter": "mm",
        "depth": "mm",
        "feed_rate": "mm/min",
        "torque": "N\u00b7m",
        "power": "kW",
        "feed_per_tooth": "mm/tooth",
        "material_removal_rate": "cm\u00b3/min",
    },
    UnitSystem.IMPERIAL: {
        "diameter": "in",
        "depth": "in",
        "feed_rate": "in/min",
        "torque": "in-lb",
        "power": "HP",
        "feed_per_tooth": "in/tooth",
        "material_removal_rate": "in\u00b3/min",
    },
}


def _prompt_unit_system(default: UnitSystem, locale: str) -> UnitSystem:
    default_label = (
        translate(locale, "cli.unit_system.metric")
        if default is UnitSystem.METRIC
        else translate(locale, "cli.unit_system.imperial")
    )
    while True:
        raw = (
            input(translate(locale, "cli.prompt.unit_system", default=default_label))
            .strip()
            .lower()
        )
        if not raw:
            return default
        if raw in ("metric", "m"):
            return UnitSystem.METRIC
        if raw in ("imperial", "i"):
            return UnitSystem.IMPERIAL
        print(translate(locale, "cli.prompt.unit_system.invalid"))


def _prompt_choice(label: str, options: list[str], default: str | None, locale: str) -> str:
    options_display = ", ".join(options)
    suffix = f" ({default})" if default else ""
    while True:
        raw = input(
            translate(
                locale, "cli.prompt.choice", label=label, options=options_display, suffix=suffix
            )
        ).strip()
        if not raw and default:
            return default
        if raw in options:
            return raw
        print(translate(locale, "cli.prompt.choice.invalid", options=options_display))


def _display_label(
    entry: WorkpieceMaterial | DrillingTool | MillingTool,
    display_locale: str,
    message_locale: str,
) -> str:
    """Build a material/tool prompt option label (User Story 3, 4).

    Displays the translated name (falling back to English, research.md #7),
    resolved from ``display_locale`` — the *raw* ``MFGPARAMS_LOCALE``
    value (:func:`mfgparams.i18n.get_raw_locale`), independent of
    whether a bundled message catalog exists for it (quickstart.md Scenario
    4: a data-driven translation is shown even when the message-catalog
    locale falls back to English). Only when the entry declares a
    non-default (``"imperial"``) unit system is a unit-system suffix
    appended (FR-013), translated via ``message_locale`` (the
    catalog-resolved active locale) — this keeps the bundled, all-metric
    defaults' prompt labels byte-for-byte identical to
    pre-``005-configurable-materials-tools`` behavior (FR-014, SC-002).
    """

    name = entry.display_name(display_locale)
    if entry.unit_system == "metric":
        return name
    return translate(
        message_locale, "cli.label.unit_system_suffix", name=name, unit_system=entry.unit_system
    )


def _material_type_label(material_type: str, locale: str) -> str:
    """Return a human-readable label for a ``material_type`` id (008 FR-001).

    Prefers the ``material_type.<id>`` message-catalog entry (Constitution
    Principle VIII). Categories introduced by data alone have no catalog
    entry, which :func:`~mfgparams.i18n.has_message` reports directly, so
    those fall back to a title-cased form of the raw id. This keeps "add a
    new category without a code change" (008 FR-004) true for the prompt
    labels too, while still letting a bundled category be translated.
    """

    key = f"material_type.{material_type}"
    # Deliberately *not* `translate(...) != key`: type ids are user data, so
    # the key is dynamic, and `translate` formats its fallback template — the
    # key itself — which both collapses doubled braces (`{{alloy}}`) into a
    # false catalog hit and logs a spurious warning when stray braces make
    # that formatting raise (`al{o}y`). `has_message` answers the question
    # directly, before any formatting happens.
    if has_message(locale, key):
        return translate(locale, key)
    # `_prompt_choice` strips the user's input before comparing it to the
    # offered options, so a label carrying leading/trailing whitespace could
    # never be typed. Ids such as "-metal" normalise to " Metal", and "-"
    # normalises to whitespace only, so strip the result and fall back to the
    # raw id when nothing printable survives (008 FR-006a).
    fallback = material_type.replace("_", " ").replace("-", " ").title().strip()
    return fallback or material_type


def _unique_labels(candidates: dict[str, str]) -> dict[str, str]:
    """Return a collision-safe ``key -> label`` mapping for reverse lookup.

    Two distinct keys (tool/material names, type ids) can render the same
    translated label. Naively building the reverse ``label -> key`` map
    from such labels silently drops all but the last-inserted key for a
    colliding label, making it unreachable via the prompt (a correctness
    bug, not just a display quirk). This suffixes a colliding label with
    its own key, escalating to a numeric discriminator if that suffixed
    form is itself already taken, so every key keeps a distinct label and
    the reverse map stays a bijection. Mirrors the collision handling
    :func:`_prompt_material_type_choice` already applies to type ids.
    """

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


def _prompt_material_type_choice(
    material_types: list[str],
    default: str | None,
    locale: str,
) -> str:
    """Prompt for a material type, returning the canonical type id (008 FR-001).

    Step one of the two-step type-then-material selection flow. Uses the
    same "label dict / reverse-lookup dict" pattern as
    :func:`_prompt_material_choice` so the user picks a translated label but
    the caller receives the stable identifier.

    Because type ids are free-form and case-sensitive while labels are not,
    two distinct ids can render the same label — a user-defined
    ``material_type = "Metal"`` title-cases to the same ``"Metal"`` as the
    bundled ``metal`` does via the message catalog. Labels are therefore
    made collision-safe by :func:`_unique_labels` so the mapping stays a
    bijection: no type can be made unreachable by the reverse lookup (008
    FR-006a).
    """

    display = {
        material_type: _material_type_label(material_type, locale)
        for material_type in material_types
    }
    labels_by_type = _unique_labels(display)
    types_by_label = {label: key for key, label in labels_by_type.items()}
    options = list(labels_by_type.values())
    default_label = labels_by_type.get(default) if default else None
    choice_label = _prompt_choice(
        translate(locale, "cli.label.material_type"), options, default_label, locale
    )
    return types_by_label[choice_label]


def _prompt_material_choice(
    names: list[str],
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str:
    """Prompt for a material, displaying translated name + unit system.

    Resolves the user's selection back to the canonical English ``name``
    before returning it (research.md #7), the same "label dict /
    reverse-lookup dict" pattern already used by :func:`_prompt_mode`.
    """

    materials = {name: get_material(name, config_path) for name in names}
    display = {
        name: _display_label(material, display_locale, locale)
        for name, material in materials.items()
        if material is not None
    }
    labels_by_name = _unique_labels(display)
    names_by_label = {label: name for name, label in labels_by_name.items()}
    options = list(labels_by_name.values())
    default_label = labels_by_name.get(default) if default else None
    choice_label = _prompt_choice(
        translate(locale, "cli.label.material"), options, default_label, locale
    )
    return names_by_label[choice_label]


def _prompt_tool_choice(
    names: list[str],
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str:
    """Prompt for a drilling tool, displaying translated name + unit system.

    Mirrors :func:`_prompt_material_choice` for :class:`DrillingTool`,
    including :func:`_unique_labels`'s collision-safe reverse lookup: two
    tool names (bundled or user-supplied) can render the same translated
    label, and without disambiguation the naive reverse map would silently
    make one of them unreachable from the prompt.
    """

    tools = {name: get_tool(name, config_path) for name in names}
    display = {
        name: _display_label(tool, display_locale, locale)
        for name, tool in tools.items()
        if tool is not None
    }
    labels_by_name = _unique_labels(display)
    names_by_label = {label: name for name, label in labels_by_name.items()}
    options = list(labels_by_name.values())
    default_label = labels_by_name.get(default) if default else None
    choice_label = _prompt_choice(
        translate(locale, "cli.label.tool"), options, default_label, locale
    )
    return names_by_label[choice_label]


def _prompt_number(label: str, unit: str, default: float | None, locale: str) -> float:
    if default is not None:
        suffix = translate(locale, "cli.prompt.suffix.with_default", unit=unit, default=default)
    else:
        suffix = translate(locale, "cli.prompt.suffix.no_default", unit=unit)
    while True:
        raw = input(translate(locale, "cli.prompt.number", label=label, suffix=suffix)).strip()
        if not raw and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print(translate(locale, "cli.prompt.number.invalid"))


def _prompt_diameter(
    unit: str, default: float | None, unit_system: UnitSystem, locale: str
) -> float:
    label = translate(locale, "cli.label.diameter")
    while True:
        value = _prompt_number(label, unit, default, locale)
        value_mm = in_to_mm(value) if unit_system is UnitSystem.IMPERIAL else value
        error = validate_diameter_mm(value_mm, _DEFAULT_CONFIG, locale)
        if error is None:
            return value
        print(error.message)


def _prompt_depth(unit: str, default: float | None, unit_system: UnitSystem, locale: str) -> float:
    label = translate(locale, "cli.label.depth")
    while True:
        value = _prompt_number(label, unit, default, locale)
        value_mm = in_to_mm(value) if unit_system is UnitSystem.IMPERIAL else value
        error = validate_depth_mm(value_mm, _DEFAULT_CONFIG, locale)
        if error is None:
            return value
        print(error.message)


def _prompt_optional_power(unit: str, default: float | None, locale: str) -> float | None:
    default_clause = (
        translate(locale, "cli.prompt.power.default_clause", default=default) if default else ""
    )
    suffix = translate(locale, "cli.prompt.power.suffix", unit=unit, default_clause=default_clause)
    label = translate(locale, "cli.label.power")
    raw = input(translate(locale, "cli.prompt.number", label=label, suffix=suffix)).strip()
    if not raw:
        return default
    if raw.lower() == "skip":
        return None
    try:
        return float(raw)
    except ValueError:
        print(translate(locale, "cli.prompt.power.invalid"))
        return default


_MODE_OPTION_KEYS = {
    CalculationMode.STANDARD: "cli.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "cli.mode.power_constrained",
    CalculationMode.FIXED_RPM: "cli.mode.fixed_rpm",
}


def _prompt_mode(
    default: CalculationMode, locale: str, *, allow_blank_default: bool = True
) -> CalculationMode:
    """Prompt for the calculation mode (FR-001a).

    Re-prompts on an invalid or unrecognized entry, the same as
    material/tool selection's invalid-entry behavior (base spec FR-010).

    ``allow_blank_default`` distinguishes the two specs sharing this
    helper: drilling's 002 spec (Clarifications 2026-07-11) treats a blank
    entry the same as material/tool selection, i.e. it accepts the current
    ``default``; milling's 010 spec (Clarifications 2026-08-19) instead
    requires the mode prompt to have no blank/default option at all — an
    empty entry there MUST be re-prompted, never silently falling back to
    a default mode. Only milling passes ``allow_blank_default=False``, so
    drilling's original blank-accepts-current-mode behavior is unaffected.
    """

    labels_by_mode = {m: translate(locale, key) for m, key in _MODE_OPTION_KEYS.items()}
    modes_by_label = {label: m for m, label in labels_by_mode.items()}
    options = list(labels_by_mode.values())
    label = translate(locale, "cli.label.mode")

    default_label = labels_by_mode[default] if allow_blank_default else None
    choice = _prompt_choice(label, options, default_label, locale)
    return modes_by_label[choice]


def _prompt_required_power(unit: str, default: float | None, locale: str) -> float:
    """Prompt for a required available-power value (power-constrained mode).

    A blank, non-numeric, or non-finite (``inf``/``nan``) entry re-prompts
    as a validation failure (FR-002; spec.md Clarifications 2026-07-11) —
    never treated as ``MODE_CONFLICT`` — unless a default is available (a
    retained editable default from a prior loop iteration in the same
    mode), in which case blank accepts it.
    """

    label = translate(locale, "cli.label.power_required")
    while True:
        value = _prompt_number(label, unit, default, locale)
        if math.isfinite(value) and value > 0:
            return value
        print(translate(locale, "cli.prompt.power_required.invalid"))


def _prompt_target_rpm(default: float | None, locale: str) -> float:
    """Prompt for a required target spindle RPM (fixed-RPM mode).

    A blank, non-numeric, or non-finite (``inf``/``nan``) entry re-prompts
    as a validation failure (FR-005, FR-007), unless a default is
    available (a retained editable default from a prior loop iteration in
    the same mode).
    """

    label = translate(locale, "cli.label.target_rpm")
    while True:
        value = _prompt_number(label, "RPM", default, locale)
        if math.isfinite(value) and value > 0:
            return value
        print(translate(locale, "cli.prompt.target_rpm.invalid"))


_SPINDLE_SPEED_MODE_LABEL_KEYS = {
    CalculationMode.STANDARD: "cli.result.spindle_speed.mode.standard",
    CalculationMode.POWER_CONSTRAINED: "cli.result.spindle_speed.mode.power_constrained",
    CalculationMode.FIXED_RPM: "cli.result.spindle_speed.mode.fixed_rpm",
}


def _display_result(result, labels: dict[str, str], locale: str) -> None:
    if result.error is not None:
        print(translate(locale, "cli.result.error", message=result.error.message))
        return

    print()
    mode_label = translate(locale, _SPINDLE_SPEED_MODE_LABEL_KEYS[result.mode])
    mode_suffix = translate(locale, "cli.result.spindle_speed.mode_suffix", label=mode_label)
    print(
        translate(locale, "cli.result.spindle_speed", value=f"{result.spindle_speed_rpm:.1f}")
        + mode_suffix
    )
    print(
        translate(
            locale,
            "cli.result.feed_rate",
            value=f"{result.feed_rate:.1f}",
            unit=labels["feed_rate"],
        )
    )
    print(translate(locale, "cli.result.machining_time", value=f"{result.machining_time:.2f}"))
    print(
        translate(locale, "cli.result.torque", value=f"{result.torque:.1f}", unit=labels["torque"])
    )
    print(
        translate(
            locale,
            "cli.result.power_required",
            value=f"{result.power_required:.2f}",
            unit=labels["power"],
        )
    )
    if result.material_removal_rate is not None:
        print(
            translate(
                locale,
                "cli.result.material_removal_rate",
                value=f"{result.material_removal_rate:.2f}",
                unit=labels["material_removal_rate"],
            )
        )
    if result.feasibility_warning:
        print(translate(locale, "cli.result.warning", message=result.feasibility_warning))
    print()


def _resolve_materials_config(materials_config_path: str | None, locale: str) -> None:
    """Validate ``materials_config_path`` once at CLI startup and print any notice.

    Raises :class:`SystemExit` (after printing a translated error, no raw
    traceback) if the file exists but is malformed or invalid
    (``RegistryConfigError``, FR-007). If the path is missing/unreadable,
    prints the translated non-fatal notice and returns normally, so the
    REPL proceeds with bundled defaults only (FR-005). Does nothing if
    ``materials_config_path`` is ``None`` (contracts/library-cli-extensions.md
    "Startup sequence").
    """

    if materials_config_path is None:
        return

    try:
        # Triggers the full parse/duplicate/validate/convert path for
        # materials and every tool catalog (drilling and milling), exactly
        # as the REPL loop will use them (FR-007's "at startup" guarantee
        # covers all config-driven catalogs, not just drilling's).
        list_materials(config_path=materials_config_path)
        list_tools(config_path=materials_config_path)
        list_end_mill_tools(config_path=materials_config_path)
        list_face_mill_tools(config_path=materials_config_path)
    except RegistryConfigError as exc:
        print(translate(locale, exc.message_key, **exc.kwargs))
        raise SystemExit(1) from exc

    notice_key, notice_kwargs = materials_load_notice(materials_config_path)
    if notice_key:
        print(translate(locale, notice_key, **dict(notice_kwargs)))


@dataclass
class _DrillingSessionState:
    """Editable defaults carried across drilling REPL iterations.

    Before the operation-selection refactor these were locals of ``run()``'s
    loop, so answering "yes" to run-again offered the previous answers as
    defaults. ``run()`` now owns one instance per REPL session and passes it
    back into each drilling session, preserving that behaviour exactly
    (FR-002, SC-005).
    """

    unit_system: UnitSystem = UnitSystem.METRIC
    material_type: str | None = None
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    depth: float | None = None
    available_power: float | None = None
    mode: CalculationMode = CalculationMode.STANDARD
    target_rpm: float | None = None
    previous_mode: CalculationMode = CalculationMode.STANDARD


def _run_drilling_session(
    state: _DrillingSessionState,
    materials_config_path: str | None,
    locale: str,
    display_locale: str,
) -> None:
    """Run one drilling prompt/calculate/display pass.

    This is the pre-``009-milling-calculations`` body of :func:`run`'s loop,
    moved verbatim so drilling behaviour is unchanged by the introduction of
    the operation-selection prompt (FR-002, SC-005); the only edits are the
    replacement of the loop's locals with ``state`` fields and the removal of
    the run-again prompt, which :func:`run` now owns so the user is re-asked
    for the operation on each iteration (FR-017).

    Args:
        state: The session's editable defaults, updated in place.
        materials_config_path: Optional user materials/tools configuration
            path, forwarded unchanged to every registry/``calculate()`` call.
        locale: The session's resolved message-catalog locale.
        display_locale: The raw ``MFGPARAMS_LOCALE`` value, used for
            data-driven material/tool name translation.
    """

    material_types = list_material_types(config_path=materials_config_path)
    tools = list_tools(config_path=materials_config_path)

    state.unit_system = _prompt_unit_system(state.unit_system, locale)
    labels = UNIT_LABELS[state.unit_system]
    state.mode = _prompt_mode(state.mode, locale)
    if state.mode is not state.previous_mode:
        # Loop re-run mode switch (FR-013, spec.md Clarifications
        # 2026-07-11): clear mode-specific values rather than carrying
        # them over as editable defaults. Shared inputs (unit system,
        # material, tool, diameter, depth) are unaffected.
        state.target_rpm = None
        state.available_power = None
    state.previous_mode = state.mode
    # Two-step material selection (008 FR-001, FR-002): pick a category
    # first, then a material within it. A remembered material from a
    # different category is silently dropped as a default by
    # `_prompt_material_choice`, which resolves defaults against the
    # options it was given (008 FR-011).
    state.material_type = _prompt_material_type_choice(material_types, state.material_type, locale)
    materials = list_materials(config_path=materials_config_path, material_type=state.material_type)
    state.material = _prompt_material_choice(
        materials, materials_config_path, state.material, locale, display_locale
    )
    state.tool = _prompt_tool_choice(
        tools, materials_config_path, state.tool, locale, display_locale
    )
    state.diameter = _prompt_diameter(labels["diameter"], state.diameter, state.unit_system, locale)
    state.depth = _prompt_depth(labels["depth"], state.depth, state.unit_system, locale)

    if state.mode is CalculationMode.POWER_CONSTRAINED:
        state.available_power = _prompt_required_power(
            labels["power"], state.available_power, locale
        )
    elif state.mode is CalculationMode.FIXED_RPM:
        state.target_rpm = _prompt_target_rpm(state.target_rpm, locale)
        state.available_power = _prompt_optional_power(
            labels["power"], state.available_power, locale
        )
    else:
        state.available_power = _prompt_optional_power(
            labels["power"], state.available_power, locale
        )

    result = calculate(
        diameter=state.diameter,
        depth=state.depth,
        material=state.material,
        tool=state.tool,
        unit_system=state.unit_system,
        available_power=state.available_power,
        locale=locale,
        mode=state.mode,
        target_rpm=state.target_rpm,
        materials_config_path=materials_config_path,
    )
    _display_result(result, labels, locale)


_OPERATION_OPTION_KEYS = {
    MachiningOperation.DRILLING: "cli.operation.drilling",
    MachiningOperation.MILLING: "cli.operation.milling",
}

_MILLING_SUB_OPERATION_OPTION_KEYS = {
    MillingSubOperation.END_MILLING: "cli.milling_sub_operation.end_milling",
    MillingSubOperation.FACE_MILLING: "cli.milling_sub_operation.face_milling",
}


def _prompt_operation(default: MachiningOperation, locale: str) -> MachiningOperation:
    """Prompt for the machining operation (FR-001).

    Structurally similar to :func:`_prompt_mode` for invalid entries: an
    unrecognized entry re-prompts with a catalog-sourced message and MUST
    NOT silently fall back to a default operation (Acceptance Scenario 4).
    Unlike :func:`_prompt_mode` (which has no blank/default option), a
    blank entry here accepts the offered default.
    """

    labels_by_operation = {op: translate(locale, key) for op, key in _OPERATION_OPTION_KEYS.items()}
    operations_by_label = {label: op for op, label in labels_by_operation.items()}
    label = translate(locale, "cli.label.operation")

    choice = _prompt_choice(
        label, list(labels_by_operation.values()), labels_by_operation[default], locale
    )
    return operations_by_label[choice]


def _prompt_milling_sub_operation(default: MillingSubOperation, locale: str) -> MillingSubOperation:
    """Prompt for the milling sub-operation (FR-003, Acceptance Scenario 3).

    Structurally identical to :func:`_prompt_operation`, over
    :class:`~mfgparams.models.MillingSubOperation`.
    """

    labels_by_sub = {
        sub: translate(locale, key) for sub, key in _MILLING_SUB_OPERATION_OPTION_KEYS.items()
    }
    subs_by_label = {label: sub for sub, label in labels_by_sub.items()}
    label = translate(locale, "cli.label.milling_sub_operation")

    choice = _prompt_choice(label, list(labels_by_sub.values()), labels_by_sub[default], locale)
    return subs_by_label[choice]


@dataclass
class _MillingSessionState:
    """Editable defaults carried across milling REPL iterations (FR-017).

    One instance per milling sub-operation, so re-selecting end milling
    offers the previous *end*-milling answers as defaults without face
    milling's answers leaking in.
    """

    unit_system: UnitSystem = UnitSystem.METRIC
    material_type: str | None = None
    material: str | None = None
    tool: str | None = None
    diameter: float | None = None
    axial_depth_of_cut: float | None = None
    radial_engagement: float | None = None
    feed_per_tooth: float | None = None
    number_of_teeth: float | None = None
    length_of_cut: float | None = None
    available_power: float | None = None
    mode: CalculationMode = CalculationMode.STANDARD
    target_rpm: float | None = None
    previous_mode: CalculationMode = CalculationMode.STANDARD

    def resolved(self) -> _ResolvedMillingInputs:
        """Return the prompted inputs with their "not answered yet" state gone.

        Every field starts as ``None`` so the first iteration offers no
        default, but a session always prompts for all of them before
        calculating. This narrows the types for the ``calculate_*`` call and
        fails loudly rather than silently passing ``None`` into the library
        if a future edit ever skips a prompt.
        """

        missing = [
            name
            for name in (
                "material",
                "tool",
                "diameter",
                "axial_depth_of_cut",
                "radial_engagement",
                "feed_per_tooth",
                "number_of_teeth",
                "length_of_cut",
            )
            if getattr(self, name) is None
        ]
        if missing:
            raise RuntimeError(f"milling inputs were not fully prompted: {missing}")

        return _ResolvedMillingInputs(
            material=cast(str, self.material),
            tool=cast(str, self.tool),
            diameter=cast(float, self.diameter),
            axial_depth_of_cut=cast(float, self.axial_depth_of_cut),
            radial_engagement=cast(float, self.radial_engagement),
            feed_per_tooth=cast(float, self.feed_per_tooth),
            number_of_teeth=cast(float, self.number_of_teeth),
            length_of_cut=cast(float, self.length_of_cut),
        )


@dataclass(frozen=True)
class _ResolvedMillingInputs:
    """A fully-answered milling input set, ready to pass to the library."""

    material: str
    tool: str
    diameter: float
    axial_depth_of_cut: float
    radial_engagement: float
    feed_per_tooth: float
    number_of_teeth: float
    length_of_cut: float


def _prompt_mill_tool_choice(
    names: list[str],
    resolve: Callable[[str, str | None], MillingTool | None],
    label_key: str,
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str:
    """Prompt for a milling tool, displaying translated name + unit system.

    Mirrors :func:`_prompt_tool_choice`, including its collision-safe
    :func:`_unique_labels` reverse lookup; ``resolve``/``label_key`` select
    the end-mill or face-mill registry so both sub-operations share one
    implementation (FR-004, FR-006).
    """

    tools = {name: resolve(name, config_path) for name in names}
    display = {
        name: _display_label(tool, display_locale, locale)
        for name, tool in tools.items()
        if tool is not None
    }
    labels_by_name = _unique_labels(display)
    names_by_label = {label: name for name, label in labels_by_name.items()}
    options = list(labels_by_name.values())
    default_label = labels_by_name.get(default) if default else None
    choice_label = _prompt_choice(translate(locale, label_key), options, default_label, locale)
    return names_by_label[choice_label]


def _prompt_end_mill_tool_choice(
    names: list[str],
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str:
    """Prompt for an end-mill tool (FR-004)."""

    return _prompt_mill_tool_choice(
        names,
        get_end_mill_tool,
        "cli.label.end_mill_tool",
        config_path,
        default,
        locale,
        display_locale,
    )


def _prompt_face_mill_tool_choice(
    names: list[str],
    config_path: str | None,
    default: str | None,
    locale: str,
    display_locale: str,
) -> str:
    """Prompt for a face-mill tool (FR-006)."""

    return _prompt_mill_tool_choice(
        names,
        get_face_mill_tool,
        "cli.label.face_mill_tool",
        config_path,
        default,
        locale,
        display_locale,
    )


def _prompt_validated_length(
    label_key: str,
    unit: str,
    default: float | None,
    unit_system: UnitSystem,
    locale: str,
    validate: Callable[[float], ErrorInfo | None],
) -> float:
    """Prompt for a length input, re-prompting until ``validate`` accepts it.

    Mirrors :func:`_prompt_diameter`/:func:`_prompt_depth`: the entered value
    is converted to canonical mm before validation, but the value returned is
    in the caller's unit system. An out-of-range entry re-prompts with the
    validation message — it is never silently clamped (FR-009).
    """

    label = translate(locale, label_key)
    while True:
        value = _prompt_number(label, unit, default, locale)
        value_mm = in_to_mm(value) if unit_system is UnitSystem.IMPERIAL else value
        error = validate(value_mm)
        if error is None:
            return value
        print(error.message)


def _prompt_milling_geometry(
    state: _MillingSessionState,
    engagement_label_key: str,
    labels: dict[str, str],
    locale: str,
) -> None:
    """Prompt for the six milling geometry inputs, updating ``state`` in place.

    Shared by both milling sessions; ``engagement_label_key`` selects the
    "Radial depth of cut" (end milling) or "Width of cut" (face milling)
    label for the radial engagement prompt. Prompt order follows
    contracts/cli-repl-milling.md steps 4-9.
    """

    unit_system = state.unit_system
    state.diameter = _prompt_validated_length(
        "cli.label.mill_diameter",
        labels["diameter"],
        state.diameter,
        unit_system,
        locale,
        lambda mm: validate_mill_diameter_mm(mm, _DEFAULT_CONFIG, locale),
    )
    state.axial_depth_of_cut = _prompt_validated_length(
        "cli.label.axial_depth_of_cut",
        labels["depth"],
        state.axial_depth_of_cut,
        unit_system,
        locale,
        lambda mm: validate_depth_of_cut_mm(
            mm, _DEFAULT_CONFIG, locale, "cli.label.axial_depth_of_cut"
        ),
    )
    diameter_mm = in_to_mm(state.diameter) if unit_system is UnitSystem.IMPERIAL else state.diameter
    state.radial_engagement = _prompt_validated_length(
        engagement_label_key,
        labels["depth"],
        state.radial_engagement,
        unit_system,
        locale,
        lambda mm: validate_depth_of_cut_mm(mm, _DEFAULT_CONFIG, locale, engagement_label_key)
        or validate_engagement_mm(mm, diameter_mm, locale, engagement_label_key),
    )
    state.feed_per_tooth = _prompt_validated_length(
        "cli.label.feed_per_tooth",
        labels["feed_per_tooth"],
        state.feed_per_tooth,
        unit_system,
        locale,
        lambda mm: validate_feed_per_tooth_mm(mm, locale),
    )
    state.number_of_teeth = _prompt_validated_length(
        "cli.label.number_of_teeth",
        translate(locale, "cli.prompt.number_of_teeth.unit"),
        state.number_of_teeth,
        # Tooth count is a pure count, never unit-converted.
        UnitSystem.METRIC,
        locale,
        lambda value: validate_tooth_count(value, locale),
    )
    state.length_of_cut = _prompt_validated_length(
        "cli.label.length_of_cut",
        labels["depth"],
        state.length_of_cut,
        unit_system,
        locale,
        lambda mm: validate_length_of_cut_mm(mm, _DEFAULT_CONFIG, locale),
    )


def _prompt_milling_inputs(
    state: _MillingSessionState,
    engagement_label_key: str,
    prompt_tool: Callable[[list[str], str | None, str | None, str, str], str],
    tool_names: list[str],
    materials_config_path: str | None,
    locale: str,
    display_locale: str,
) -> dict[str, str]:
    """Run the full milling prompt sequence, updating ``state`` in place.

    Implements steps 1-10 of contracts/cli-repl-milling.md in order: unit
    system, calculation mode, material type, material, tool, the six
    geometry inputs, then the mode-appropriate power/RPM prompt(s)
    (contracts/cli-repl-milling-modes-delta.md of
    ``specs/010-milling-calculation-modes``). The mode prompt is placed
    immediately after the unit-system prompt and before material-type,
    matching drilling's ``_run_drilling_session`` prompt placement exactly
    (FR-001a).

    Returns:
        The unit-label dict for the chosen unit system, for result display.
    """

    state.unit_system = _prompt_unit_system(state.unit_system, locale)
    labels = UNIT_LABELS[state.unit_system]

    state.mode = _prompt_mode(state.mode, locale, allow_blank_default=False)
    if state.mode is not state.previous_mode:
        # Loop re-run mode switch (FR-013): clear mode-specific values
        # rather than carrying them over as editable defaults. Shared
        # inputs (unit system, material, tool, geometry) are unaffected.
        state.target_rpm = None
        state.available_power = None
    state.previous_mode = state.mode

    material_types = list_material_types(config_path=materials_config_path)
    state.material_type = _prompt_material_type_choice(material_types, state.material_type, locale)
    materials = list_materials(config_path=materials_config_path, material_type=state.material_type)
    state.material = _prompt_material_choice(
        materials, materials_config_path, state.material, locale, display_locale
    )
    state.tool = prompt_tool(tool_names, materials_config_path, state.tool, locale, display_locale)

    _prompt_milling_geometry(state, engagement_label_key, labels, locale)

    if state.mode is CalculationMode.POWER_CONSTRAINED:
        state.available_power = _prompt_required_power(
            labels["power"], state.available_power, locale
        )
    elif state.mode is CalculationMode.FIXED_RPM:
        state.target_rpm = _prompt_target_rpm(state.target_rpm, locale)
        state.available_power = _prompt_optional_power(
            labels["power"], state.available_power, locale
        )
    else:
        state.available_power = _prompt_optional_power(
            labels["power"], state.available_power, locale
        )
    return labels


def _run_end_milling_session(
    state: _MillingSessionState,
    materials_config_path: str | None,
    locale: str,
    display_locale: str,
) -> None:
    """Run one end-milling prompt/calculate/display pass (FR-004, FR-005)."""

    labels = _prompt_milling_inputs(
        state,
        "cli.label.radial_depth_of_cut",
        _prompt_end_mill_tool_choice,
        list_end_mill_tools(config_path=materials_config_path),
        materials_config_path,
        locale,
        display_locale,
    )
    inputs = state.resolved()
    result = calculate_end_milling(
        diameter=inputs.diameter,
        axial_depth_of_cut=inputs.axial_depth_of_cut,
        radial_depth_of_cut=inputs.radial_engagement,
        feed_per_tooth=inputs.feed_per_tooth,
        number_of_teeth=inputs.number_of_teeth,
        length_of_cut=inputs.length_of_cut,
        material=inputs.material,
        tool=inputs.tool,
        unit_system=state.unit_system,
        available_power=state.available_power,
        locale=locale,
        mode=state.mode,
        target_rpm=state.target_rpm,
        materials_config_path=materials_config_path,
    )
    _display_result(result, labels, locale)


def _run_face_milling_session(
    state: _MillingSessionState,
    materials_config_path: str | None,
    locale: str,
    display_locale: str,
) -> None:
    """Run one face-milling prompt/calculate/display pass (FR-006, FR-007)."""

    labels = _prompt_milling_inputs(
        state,
        "cli.label.width_of_cut",
        _prompt_face_mill_tool_choice,
        list_face_mill_tools(config_path=materials_config_path),
        materials_config_path,
        locale,
        display_locale,
    )
    inputs = state.resolved()
    result = calculate_face_milling(
        diameter=inputs.diameter,
        axial_depth_of_cut=inputs.axial_depth_of_cut,
        width_of_cut=inputs.radial_engagement,
        feed_per_tooth=inputs.feed_per_tooth,
        number_of_teeth=inputs.number_of_teeth,
        length_of_cut=inputs.length_of_cut,
        material=inputs.material,
        tool=inputs.tool,
        unit_system=state.unit_system,
        available_power=state.available_power,
        locale=locale,
        mode=state.mode,
        target_rpm=state.target_rpm,
        materials_config_path=materials_config_path,
    )
    _display_result(result, labels, locale)


def _run_milling_session(
    sub_operation: MillingSubOperation,
    state: _MillingSessionState,
    materials_config_path: str | None,
    locale: str,
    display_locale: str,
) -> None:
    """Dispatch to the selected milling sub-operation's session (FR-003)."""

    if sub_operation is MillingSubOperation.END_MILLING:
        _run_end_milling_session(state, materials_config_path, locale, display_locale)
    else:
        _run_face_milling_session(state, materials_config_path, locale, display_locale)


def run(materials_config_path: str | None = None) -> None:
    """Run the interactive machining-calculation REPL until the user exits.

    Each iteration asks which machining operation to calculate before any
    operation-specific prompt (FR-001), then delegates the whole prompt/
    calculate/display sequence to that operation's session function. The
    operation prompt is repeated on every iteration, so a user who answers
    yes to "run another calculation" may switch operations rather than being
    locked into the previous one (FR-017).

    Resolves the active locale exactly once, at the start of the session
    (FR-019c); it is not re-read on subsequent loop iterations even if
    ``MFGPARAMS_LOCALE`` changes in the environment mid-session.

    Args:
        materials_config_path: Optional path (resolved once at startup from
            the ``--materials-config`` CLI flag) to a user-supplied
            materials/tools configuration file. Forwarded, unchanged for
            the whole session, to every ``list_materials()``/
            ``list_tools()``/``calculate*()`` call in the REPL loop
            (research.md #3).
    """

    locale = get_locale()
    display_locale = get_raw_locale()

    _resolve_materials_config(materials_config_path, locale)

    operation = MachiningOperation.DRILLING
    sub_operation = MillingSubOperation.END_MILLING
    drilling_state = _DrillingSessionState()
    milling_states = {sub: _MillingSessionState() for sub in MillingSubOperation}

    while True:
        operation = _prompt_operation(operation, locale)
        if operation is MachiningOperation.DRILLING:
            _run_drilling_session(drilling_state, materials_config_path, locale, display_locale)
        else:
            sub_operation = _prompt_milling_sub_operation(sub_operation, locale)
            _run_milling_session(
                sub_operation,
                milling_states[sub_operation],
                materials_config_path,
                locale,
                display_locale,
            )

        again = input(translate(locale, "cli.prompt.run_again")).strip().lower()
        if again not in ("y", "yes"):
            break


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments (currently just ``--materials-config``, FR-002)."""

    parser = argparse.ArgumentParser(prog="mfgparams")
    parser.add_argument(
        "--materials-config",
        dest="materials_config",
        default=None,
        metavar="PATH",
        help=(
            "Optional path to a TOML file adding/overriding materials and "
            "drilling tools (see contracts/materials-config-schema.md)."
        ),
    )
    return parser.parse_args(argv)


def main() -> int:
    """Console-script entry point (``mfgparams`` / ``python -m mfgparams``).

    Returns the process exit status. ``0`` covers both a completed session and
    an interrupted one: Ctrl-C and EOF are how a user *leaves* this REPL, not
    failures, and both exited 0 before this became an explicit return.
    """

    configure_logging()
    args = _parse_args()
    try:
        run(materials_config_path=args.materials_config)
    except (KeyboardInterrupt, EOFError):
        print()
    return 0
