"""The Configuration screen: read-only view of the active materials/tools
registry (FR-014/FR-015, data-model.md's ConfigurationView, research.md #4).

Deliberately **not** a create/edit UI — resolved via `/speckit-clarify`:
view-only, matching what the REPL already exposed (viewing an existing
registry via `--materials-config`), not new authoring capability. Now a
pure render function (like `screens/about.py`/`screens/help.py`) embedded
in the persistent body rather than its own dialog loop -- since it's
view-only, there is nothing to select/submit, so a static, complete
listing (all material types with their materials, plus all three tool
registries per FR-015) needs no interactive drill-down the way the old
per-type dialog did.
"""

from __future__ import annotations

from prompt_toolkit.formatted_text import StyleAndTextTuples

from mfgparams import (
    list_end_mill_tools,
    list_face_mill_tools,
    list_material_types,
    list_materials,
    list_tools,
    list_turning_tools,
)
from mfgparams.console.i18n import translate
from mfgparams.console.tui import forms


def render_configuration(
    materials_config_path: str | None, locale: str, display_locale: str
) -> StyleAndTextTuples:
    path_key = (
        "tui.configuration.path_label.set"
        if materials_config_path
        else "tui.configuration.path_label.default"
    )
    path_line = (
        translate(locale, path_key, path=materials_config_path)
        if materials_config_path
        else translate(locale, path_key)
    )

    material_types = list_material_types(config_path=materials_config_path)
    fragments: StyleAndTextTuples = [
        ("class:pane-title", f"{translate(locale, 'tui.configuration.title')}\n"),
        ("", f"{path_line}\n\n"),
    ]

    type_labels = ", ".join(forms.material_type_label(mt, locale) for mt in material_types) or "-"
    fragments.append(
        (
            "",
            translate(locale, "tui.configuration.section.material_types", items=type_labels) + "\n",
        )
    )
    for material_type in material_types:
        materials = list_materials(config_path=materials_config_path, material_type=material_type)
        fragments.append(
            (
                "",
                translate(
                    locale,
                    "tui.configuration.section.materials",
                    material_type=forms.material_type_label(material_type, locale),
                    items=", ".join(materials) or "-",
                )
                + "\n",
            )
        )

    fragments.append(("", "\n"))
    fragments.append(
        (
            "",
            translate(
                locale,
                "tui.configuration.section.tools",
                items=", ".join(list_tools(config_path=materials_config_path)) or "-",
            )
            + "\n",
        )
    )
    fragments.append(
        (
            "",
            translate(
                locale,
                "tui.configuration.section.end_mill_tools",
                items=", ".join(list_end_mill_tools(config_path=materials_config_path)) or "-",
            )
            + "\n",
        )
    )
    fragments.append(
        (
            "",
            translate(
                locale,
                "tui.configuration.section.face_mill_tools",
                items=", ".join(list_face_mill_tools(config_path=materials_config_path)) or "-",
            )
            + "\n",
        )
    )
    fragments.append(
        (
            "",
            translate(
                locale,
                "tui.configuration.section.turning_tools",
                items=", ".join(list_turning_tools(config_path=materials_config_path)) or "-",
            )
            + "\n",
        )
    )
    return fragments
