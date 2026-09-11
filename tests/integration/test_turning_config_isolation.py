"""Registry isolation between turning and the other three tool tables,
mirroring tests/integration/test_milling_config_isolation.py.

Users supply a *single* configuration file for the whole application
(contracts/turning-tools-config-schema.md "Section isolation"), so
turning's ``turning_tools`` table must not leak into (or be leaked into
by) drilling's ``tools``, milling's ``end_mill_tools``/``face_mill_tools``,
or the materials registry — added per a Copilot review finding: this
promised isolation had no dedicated regression test.
"""

import pytest

from mfgparams import (
    calculate_turning,
    list_end_mill_tools,
    list_face_mill_tools,
    list_materials,
    list_tools,
    list_turning_tools,
)
from mfgparams.registry_config import clear_cache


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    clear_cache()
    yield
    clear_cache()


def _write(tmp_path, body: str) -> str:
    path = tmp_path / "config.toml"
    path.write_text(body)
    return str(path)


BUNDLED_DRILLING_TOOLS = list_tools()
BUNDLED_END_MILL_TOOLS = list_end_mill_tools()
BUNDLED_FACE_MILL_TOOLS = list_face_mill_tools()
BUNDLED_TURNING_TOOLS = list_turning_tools()
BUNDLED_MATERIALS = list_materials()


def test_turning_only_config_leaves_every_other_registry_untouched(tmp_path):
    path = _write(
        tmp_path,
        """
        [[turning_tools]]
        name = "Ceramic"
        cutting_speed_factor = 5.0
        feed_factor = 1.0
        """,
    )

    assert "Ceramic" in list_turning_tools(path)
    assert list_tools(config_path=path) == BUNDLED_DRILLING_TOOLS
    assert list_end_mill_tools(config_path=path) == BUNDLED_END_MILL_TOOLS
    assert list_face_mill_tools(config_path=path) == BUNDLED_FACE_MILL_TOOLS
    assert list_materials(config_path=path) == BUNDLED_MATERIALS
    # ... and it does not leak into the other three tool tables either.
    assert "Ceramic" not in list_tools()
    assert "Ceramic" not in list_end_mill_tools()
    assert "Ceramic" not in list_face_mill_tools()


def test_other_registries_only_config_leaves_turning_untouched(tmp_path):
    path = _write(
        tmp_path,
        """
        [[tools]]
        name = "Ceramic"
        cutting_speed_factor = 5.0
        feed_factor = 1.0

        [[end_mill_tools]]
        name = "Ceramic"
        cutting_speed_factor = 5.0

        [[face_mill_tools]]
        name = "Ceramic"
        cutting_speed_factor = 5.0
        """,
    )

    assert list_turning_tools(config_path=path) == BUNDLED_TURNING_TOOLS
    assert "Ceramic" not in list_turning_tools(path)


def test_all_four_tool_tables_can_override_the_same_name_independently(tmp_path):
    """A shared name ("Carbide") across all four tables' own overrides must
    each apply only to its own registry — no cross-contamination."""

    path = _write(
        tmp_path,
        """
        [[tools]]
        name = "Carbide"
        cutting_speed_factor = 3.0
        feed_factor = 1.2

        [[end_mill_tools]]
        name = "Carbide"
        cutting_speed_factor = 4.0

        [[face_mill_tools]]
        name = "Carbide"
        cutting_speed_factor = 6.0

        [[turning_tools]]
        name = "Carbide"
        cutting_speed_factor = 9.0
        feed_factor = 1.5
        """,
    )

    from mfgparams.processes.machining.drilling.tools import get_tool
    from mfgparams.processes.machining.milling.end_milling.tools import get_end_mill_tool
    from mfgparams.processes.machining.milling.face_milling.tools import get_face_mill_tool
    from mfgparams.processes.machining.turning.tools import get_turning_tool

    assert get_tool("Carbide", path).cutting_speed_factor == 3.0
    assert get_end_mill_tool("Carbide", path).cutting_speed_factor == 4.0
    assert get_face_mill_tool("Carbide", path).cutting_speed_factor == 6.0
    assert get_turning_tool("Carbide", path).cutting_speed_factor == 9.0
    # Bundled defaults for each, untouched.
    assert get_tool("Carbide").cutting_speed_factor == 2.5
    assert get_turning_tool("Carbide").cutting_speed_factor == 2.4


def test_turning_still_calculates_with_a_drilling_only_config(tmp_path):
    """A drilling tool entry has the same field shape as turning's, but
    turning must not see it under drilling's own table key."""

    path = _write(
        tmp_path,
        """
        [[tools]]
        name = "Ceramic"
        cutting_speed_factor = 5.0
        feed_factor = 1.0
        """,
    )

    result = calculate_turning(
        diameter=40.0,
        depth_of_cut=2.0,
        length_of_cut=100.0,
        material="Mild Steel",
        tool="Carbide",
        materials_config_path=path,
    )
    assert result.error is None


def test_the_four_registries_use_distinct_table_keys():
    """Guard the invariant directly, not just its observable consequences."""

    from mfgparams.processes.machining.drilling import tools as drilling_tools
    from mfgparams.processes.machining.milling.end_milling import tools as end_tools
    from mfgparams.processes.machining.milling.face_milling import tools as face_tools
    from mfgparams.processes.machining.turning import tools as turning_tools

    keys = {
        drilling_tools._TABLE_KEY,
        end_tools._TABLE_KEY,
        face_tools._TABLE_KEY,
        turning_tools._TABLE_KEY,
    }
    assert len(keys) == 4
