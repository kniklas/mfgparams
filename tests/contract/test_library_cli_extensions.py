"""Contract test (T025): calculate()/list_materials()/list_tools()/get_material()/
get_tool() gain the new optional parameters described in
`contracts/library-cli-extensions.md` without breaking any existing call signature.
"""

from __future__ import annotations

import inspect

from mfgparams import calculate
from mfgparams.operations.drilling.tools import get_tool, list_tools
from mfgparams.registry import get_material, list_materials


def test_calculate_gains_materials_config_path_kwarg():
    sig = inspect.signature(calculate)
    assert "materials_config_path" in sig.parameters
    assert sig.parameters["materials_config_path"].default is None
    # Existing config_path parameter is unaffected/still present (FR-017).
    assert "config_path" in sig.parameters


def test_list_materials_gains_config_path_kwarg():
    sig = inspect.signature(list_materials)
    assert "config_path" in sig.parameters
    assert sig.parameters["config_path"].default is None


def test_get_material_gains_config_path_kwarg():
    sig = inspect.signature(get_material)
    assert "config_path" in sig.parameters
    assert sig.parameters["config_path"].default is None


def test_list_tools_gains_config_path_kwarg():
    sig = inspect.signature(list_tools)
    assert "config_path" in sig.parameters
    assert sig.parameters["config_path"].default is None


def test_get_tool_gains_config_path_kwarg():
    sig = inspect.signature(get_tool)
    assert "config_path" in sig.parameters
    assert sig.parameters["config_path"].default is None


def test_calculate_existing_call_signature_unbroken():
    # No materials_config_path/config_path supplied at all - existing callers
    # continue to work unchanged (FR-014).
    result = calculate(diameter=10, depth=25, material="Mild Steel", tool="Carbide")
    assert result.error is None


def test_list_materials_existing_call_signature_unbroken():
    assert list_materials() == list_materials(config_path=None)


def test_list_tools_existing_call_signature_unbroken():
    assert list_tools() == list_tools(config_path=None)
