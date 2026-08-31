"""English (``en``) message catalog — the default and fallback locale.

Message IDs are stable and language-independent; do not rename an existing
key when editing its English text (other locale modules and tests key off
these IDs). See ``specs/001-metal-drilling-calc/data-model.md`` (Message
Catalog) for the entity definition this module implements.
"""

from __future__ import annotations

MESSAGES: dict[str, str] = {
    # --- Console availability (mfgparams/__main__.py, FR-011) ---
    #
    # MUST stay in the core catalog when slice 015 relocates the others into
    # the console. This message exists to say the console is unavailable, so
    # looking it up from a catalog that lives inside the console would fail
    # exactly when it is needed and hand the user the traceback FR-011 exists
    # to prevent (contracts/console-entry-contract.md, research.md #4).
    "console.missing_dependency": (
        "The interactive console is not available: it needs {module}, which is "
        "not installed.\nInstall it with:  pip install mfgparams[console]"
    ),
    # --- Interactive text interface (console/cli.py) prompts and labels ---
    "cli.prompt.unit_system": "Unit system [metric/imperial] ({default}): ",
    "cli.prompt.unit_system.invalid": "Please enter 'metric' or 'imperial'.",
    "cli.unit_system.metric": "metric",
    "cli.unit_system.imperial": "imperial",
    "cli.prompt.choice": "{label} ({options}){suffix}: ",
    "cli.prompt.choice.invalid": "Please choose one of: {options}",
    "cli.prompt.number": "{label}{suffix}: ",
    "cli.prompt.number.invalid": "Please enter a numeric value.",
    "cli.prompt.suffix.with_default": " ({unit}, default {default})",
    "cli.prompt.suffix.no_default": " ({unit})",
    "cli.prompt.power.suffix": " ({unit}, blank if unknown{default_clause})",
    "cli.prompt.power.default_clause": ", default {default}",
    "cli.prompt.power.invalid": "Ignoring non-numeric power value.",
    "cli.label.diameter": "Drill diameter",
    "cli.label.depth": "Hole depth",
    "cli.label.power": "Available power",
    "cli.label.material": "Material",
    "cli.label.tool": "Drilling tool",
    # --- Material-type (category) selection, specs/008-material-categorization ---
    # `material_type.<id>` supplies a human-readable, translatable label for a
    # category id. Unknown ids intentionally have no entry: cli.py falls back to
    # a title-cased form of the raw id so a category added by data alone still
    # displays sensibly with no code or catalog change (008 FR-004).
    "cli.label.material_type": "Material type",
    "material_type.metal": "Metal",
    "material_type.wood": "Wood",
    "material_type.uncategorized": "Uncategorized",
    "cli.prompt.run_again": "Run another calculation? [y/N]: ",
    "cli.result.error": "\nError: {message}\n",
    "cli.result.spindle_speed": "Spindle speed:     {value} RPM",
    "cli.result.spindle_speed.mode_suffix": "   ({label})",
    "cli.result.spindle_speed.mode.standard": "recommended",
    "cli.result.spindle_speed.mode.power_constrained": "adjusted to fit available power",
    "cli.result.spindle_speed.mode.fixed_rpm": "user-specified",
    "cli.result.feed_rate": "Feed rate:         {value} {unit}",
    "cli.result.machining_time": "Machining time:    {value} min",
    "cli.result.torque": "Torque:            {value} {unit}",
    "cli.result.power_required": "Power required:    {value} {unit}",
    "cli.result.warning": "Warning: {message}",
    # --- Calculation-mode selection prompt (FR-001a) ---
    "cli.label.mode": "Calculation mode",
    "cli.mode.standard": "standard",
    "cli.mode.power_constrained": "power-constrained",
    "cli.mode.fixed_rpm": "fixed-rpm",
    "cli.label.power_required": "Available power",
    "cli.prompt.power_required.invalid": (
        "Please enter a positive numeric value for available power."
    ),
    "cli.label.target_rpm": "Target spindle speed",
    "cli.prompt.target_rpm.invalid": (
        "Please enter a positive numeric value for target spindle speed."
    ),
    # --- Validation / structured errors (validation.py, machining.drilling) ---
    "error.invalid_diameter.zero": "Drill diameter must be greater than 0.",
    "error.invalid_diameter.max": "Drill diameter must not exceed {max_diameter_mm:g} mm.",
    "error.invalid_depth.zero": "Hole depth must be greater than 0.",
    "error.invalid_depth.max": "Hole depth must not exceed {max_depth_mm:g} mm.",
    "error.missing_material": "A workpiece material must be selected.",
    "error.missing_tool": "A drilling tool must be selected.",
    "error.unknown_material": "Unknown workpiece material: {material!r}.",
    "error.unknown_tool": "Unknown drilling tool: {tool!r}.",
    "error.unusable_material": (
        "Workpiece material {material!r} is registered but unusable for calculation: {details}."
    ),
    "error.invalid_target_rpm": "Target spindle speed must be a positive, finite number.",
    "error.mode_conflict": (
        "Power-constrained and fixed-RPM inputs cannot be combined in one "
        "request, and power-constrained mode requires an available power "
        "value."
    ),
    "error.infeasible_power_budget": (
        "No spindle speed keeps the required power within the supplied " "available power budget."
    ),
    "error.invalid_available_power": "Available power must be a positive, finite number.",
    "error.calculation_overflow": (
        "The supplied inputs produce a result too large to represent; reduce the feed per "
        "tooth, target spindle speed, or other extreme input and try again."
    ),
    "warning.feasibility": (
        "Required power ({required_kw:.2f} kW) exceeds the available "
        "power ({available_kw:.2f} kW)."
    ),
    # --- Materials/tools configuration file notices/errors (005) ---
    "notice.materials_config.not_found": (
        "Materials/tools configuration file {path!r} was not found or is not "
        "readable; continuing with the built-in defaults."
    ),
    "error.materials_config.malformed": (
        "Materials/tools configuration file {path!r} could not be parsed as "
        "valid TOML: {details}"
    ),
    "error.materials_config.duplicate_entry": (
        "Materials/tools configuration file {path!r} defines more than one "
        "{kind} named {name!r}."
    ),
    "error.materials_config.invalid_entry": (
        "Materials/tools configuration file {path!r} has an invalid {kind} "
        "entry {name!r}: {details}"
    ),
    "cli.label.unit_system_suffix": "{name} [{unit_system}]",
    # --- Operation / milling sub-operation selection (009 FR-001, FR-003) ---
    "cli.label.operation": "Machining operation",
    "cli.operation.drilling": "drilling",
    "cli.operation.milling": "milling",
    "cli.label.milling_sub_operation": "Milling operation",
    "cli.milling_sub_operation.end_milling": "end milling",
    "cli.milling_sub_operation.face_milling": "face milling",
    # --- Milling input prompts and labels (009 FR-004, FR-006) ---
    "cli.label.mill_diameter": "Cutter diameter",
    "cli.label.end_mill_tool": "End-mill tool",
    "cli.label.face_mill_tool": "Face-mill tool",
    "cli.label.axial_depth_of_cut": "Axial depth of cut",
    "cli.label.radial_depth_of_cut": "Radial depth of cut",
    "cli.label.width_of_cut": "Width of cut",
    "cli.label.feed_per_tooth": "Feed per tooth",
    "cli.label.number_of_teeth": "Number of teeth",
    "cli.label.length_of_cut": "Length of cut",
    "cli.prompt.number_of_teeth.unit": "teeth",
    "cli.result.material_removal_rate": "Material removal:  {value} {unit}",
    # --- Milling validation / structured errors (009 FR-008, FR-009, FR-018) ---
    "error.invalid_mill_diameter.zero": "Cutter diameter must be greater than 0.",
    "error.invalid_mill_diameter.max": (
        "Cutter diameter must not exceed {max_mill_diameter_mm:g} mm."
    ),
    "error.invalid_depth_of_cut.zero": "{label} must be greater than 0.",
    "error.invalid_depth_of_cut.max": "{label} must not exceed {max_depth_of_cut_mm:g} mm.",
    "error.invalid_engagement": "{label} must not exceed the cutter diameter ({diameter_mm:g} mm).",
    "error.invalid_feed_per_tooth": "Feed per tooth must be greater than 0.",
    "error.invalid_tooth_count": "Number of teeth must be greater than 0.",
    "error.invalid_tooth_count.fractional": "Number of teeth must be a whole number.",
    "error.invalid_length_of_cut.zero": "Length of cut must be greater than 0.",
    "error.invalid_length_of_cut.max": (
        "Length of cut must not exceed {max_length_of_cut_mm:g} mm."
    ),
    "error.missing_mill_tool": "A milling tool must be selected.",
    "error.unknown_mill_tool": "Unknown milling tool: {tool!r}.",
}
