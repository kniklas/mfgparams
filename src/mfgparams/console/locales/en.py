"""English (``en``) message catalog for the console — the default and fallback locale.

Message IDs are stable and language-independent; do not rename an existing
key when editing its English text (other locale modules and tests key off
these IDs). See ``specs/015-console-i18n-relocation/data-model.md`` for the
entity definition this module implements, and
``specs/015-console-i18n-relocation/contracts/catalogue-ownership-contract.md``
for which strings belong here versus in :mod:`mfgparams.locales.en`.

Relocated verbatim from :mod:`mfgparams.locales.en` (specs/015-console-i18n
-relocation FR-001, research.md #4) — every ``cli.*``/``material_type.*``
entry that catalog held, unchanged in text.
"""

from __future__ import annotations

MESSAGES: dict[str, str] = {
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
    # These three are also duplicated in mfgparams.locales.en: core embeds
    # them inside error text it must be able to build without the console
    # installed (see that file's comment on this same trio; FR-004's
    # narrow second exception, found during FR-005 implementation).
    "cli.label.axial_depth_of_cut": "Axial depth of cut",
    "cli.label.radial_depth_of_cut": "Radial depth of cut",
    "cli.label.width_of_cut": "Width of cut",
    "cli.label.feed_per_tooth": "Feed per tooth",
    "cli.label.number_of_teeth": "Number of teeth",
    "cli.label.length_of_cut": "Length of cut",
    "cli.prompt.number_of_teeth.unit": "teeth",
    "cli.result.material_removal_rate": "Material removal:  {value} {unit}",
}
