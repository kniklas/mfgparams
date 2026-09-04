"""English (``en``) message catalog — the default and fallback locale.

Message IDs are stable and language-independent; do not rename an existing
key when editing its English text (other locale modules and tests key off
these IDs). See ``specs/001-metal-drilling-calc/data-model.md`` (Message
Catalog) for the entity definition this module implements.

Holds only the entries that must remain reachable without the ``console``
extra installed: the console-unavailable message and error/warning/notice
text (``ErrorInfo.message`` is always English, specs/015-console-i18n
-relocation FR-005). Every ``cli.*``/``material_type.*`` UI string moved to
:mod:`mfgparams.console.locales.en` in that same feature (FR-001,
research.md #4) — see
``specs/015-console-i18n-relocation/contracts/catalogue-ownership-contract.md``.
"""

from __future__ import annotations

MESSAGES: dict[str, str] = {
    # --- Console availability (mfgparams/__main__.py, FR-011) ---
    #
    # MUST stay in the core catalog (specs/015-console-i18n-relocation FR-002,
    # inherited from specs/014-process-namespaces-extras). This message exists
    # to say the console is unavailable, so looking it up from a catalog that
    # lives inside the console would fail exactly when it is needed and hand
    # the user the traceback FR-011 exists to prevent
    # (specs/014-process-namespaces-extras/contracts/console-entry-contract.md).
    # `{command}` is built by the guard rather than written here, and both of
    # its peculiarities are load-bearing (contracts/console-entry-contract.md):
    # the requirement is *quoted*, because zsh -- the default shell on macOS --
    # globs `[console]` and aborts with `no matches found` before pip runs; and
    # it names the *running interpreter* rather than a bare `pip`, which on a
    # machine with several Pythons installs into the wrong one and reproduces
    # this very message. FR-011 promises "the exact command that fixes it", so
    # neither is cosmetic -- and neither is left where a translation could
    # break it.
    "console.missing_dependency": (
        "The interactive console is not available: it needs {module}, which is "
        "not installed.\nInstall it with:  {command}"
    ),
    # Substituted for `{module}` above when the exception carried no name.
    # Prose, so it is catalogued rather than inlined at the call site: a
    # literal there would stay English inside a translated sentence.
    "console.missing_dependency.unnamed": "a dependency",
    # --- Input labels embedded inside core error text (validation.py) ---
    #
    # These three duplicate entries in mfgparams.console.locales.en (FR-001):
    # a narrow, second exception to "one key, one catalog" (FR-004), found
    # while implementing FR-005 rather than assumed up front (spec.md
    # Assumptions originally claimed console.missing_dependency* was the
    # only such case; it was not). validate_depth_of_cut_mm/
    # validate_engagement_mm build their English `message` by embedding a
    # `{label}` resolved from one of these keys via translate() — core must
    # be able to do that without the console installed (FR-005), so core
    # needs its own copy of the text, not just console's copy for prompts.
    "cli.label.axial_depth_of_cut": "Axial depth of cut",
    "cli.label.radial_depth_of_cut": "Radial depth of cut",
    "cli.label.width_of_cut": "Width of cut",
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
