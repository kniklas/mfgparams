"""Contract test: the public milling API surface (T039, US4).

Checks the four public entry points against
``contracts/library-api-milling.md`` — importability from ``mfgparams``,
exact signatures (parameter names, order and defaults), and the documented
success/error ``CalculationResult`` shapes.

Also asserts the FR-014 module boundary statically: neither operation
package may import the other. Each may depend only on the shared top-level
modules (Constitution Principle VI), so drilling and milling can evolve
independently.
"""

import ast
import importlib
import inspect
from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path

import pytest

import mfgparams
from mfgparams import (
    calculate_end_milling,
    calculate_face_milling,
    list_end_mill_tools,
    list_face_mill_tools,
)
from mfgparams.models import CalculationMode, CalculationResult, UnitSystem

_SRC = Path(mfgparams.__file__).parent

_COMMON_TAIL = [
    ("material", inspect.Parameter.empty),
    ("tool", inspect.Parameter.empty),
    ("unit_system", UnitSystem.METRIC),
    ("available_power", None),
    ("config_path", None),
    ("locale", "en"),
    ("materials_config_path", None),
    ("mode", CalculationMode.STANDARD),
    ("target_rpm", None),
]

_EXPECTED_SIGNATURES = {
    calculate_end_milling: [
        ("diameter", inspect.Parameter.empty),
        ("axial_depth_of_cut", inspect.Parameter.empty),
        ("radial_depth_of_cut", inspect.Parameter.empty),
        ("feed_per_tooth", inspect.Parameter.empty),
        ("number_of_teeth", inspect.Parameter.empty),
        ("length_of_cut", inspect.Parameter.empty),
        *_COMMON_TAIL,
    ],
    calculate_face_milling: [
        ("diameter", inspect.Parameter.empty),
        ("axial_depth_of_cut", inspect.Parameter.empty),
        ("width_of_cut", inspect.Parameter.empty),
        ("feed_per_tooth", inspect.Parameter.empty),
        ("number_of_teeth", inspect.Parameter.empty),
        ("length_of_cut", inspect.Parameter.empty),
        *_COMMON_TAIL,
    ],
}


#: Every name ``mfgparams`` publishes, and the kind of object it must be.
#:
#: FR-005 requires the top-level surface to be *unchanged* by the
#: process-namespace restructure, so this is deliberately the whole of
#: ``__all__`` rather than the four milling entry points this file originally
#: covered: a name silently dropped, renamed, or degraded from a class to
#: something else while modules moved underneath is exactly the regression the
#: restructure could introduce, and nothing else would catch it.
_PUBLIC_SURFACE = {
    "calculate": "function",
    "calculate_end_milling": "function",
    "calculate_face_milling": "function",
    "list_end_mill_tools": "function",
    "list_face_mill_tools": "function",
    "list_material_types": "function",
    "list_materials": "function",
    "list_tools": "function",
    "UnitSystem": "enum",
    "CalculationMode": "enum",
    "CalculationResult": "dataclass",
    "ErrorInfo": "dataclass",
    "MachiningOperation": "enum",
    "MillingSubOperation": "enum",
}


def test_public_surface_is_exactly_the_documented_set():
    """``__all__`` itself must not drift -- in either direction (FR-005)."""

    assert sorted(mfgparams.__all__) == sorted(_PUBLIC_SURFACE)


@pytest.mark.parametrize("name,kind", sorted(_PUBLIC_SURFACE.items()))
def test_entry_point_is_importable_from_the_package_root(name, kind):
    assert hasattr(mfgparams, name), f"{name} is no longer importable from mfgparams"
    assert name in mfgparams.__all__, f"{name} is no longer exported"

    obj = getattr(mfgparams, name)
    if kind == "function":
        assert callable(obj) and not isinstance(obj, type), f"{name} is no longer a function"
    elif kind == "enum":
        assert isinstance(obj, type) and issubclass(obj, Enum), f"{name} is no longer an Enum"
    else:
        assert isinstance(obj, type) and is_dataclass(obj), f"{name} is no longer a dataclass"


@pytest.mark.parametrize(
    "fn,expected", _EXPECTED_SIGNATURES.items(), ids=["end_milling", "face_milling"]
)
def test_calculate_signature_matches_the_contract(fn, expected):
    parameters = list(inspect.signature(fn).parameters.values())

    assert [p.name for p in parameters] == [name for name, _ in expected]
    for parameter, (name, default) in zip(parameters, expected):
        assert parameter.default == default, f"{name} default"


@pytest.mark.parametrize(
    "fn", [list_end_mill_tools, list_face_mill_tools], ids=["end_mill", "face_mill"]
)
def test_list_tools_signature_matches_the_contract(fn):
    parameters = list(inspect.signature(fn).parameters.values())

    assert [p.name for p in parameters] == ["config_path"]
    assert parameters[0].default is None
    assert all(isinstance(name, str) for name in fn())


def test_end_milling_success_result_shape():
    result = calculate_end_milling(10.0, 2.0, 5.0, 0.05, 4, 100.0, "Mild Steel", "Carbide")

    assert isinstance(result, CalculationResult)
    assert result.error is None
    assert result.material_removal_rate is not None
    assert result.unit_system is UnitSystem.METRIC


def test_face_milling_success_result_shape():
    result = calculate_face_milling(50.0, 1.5, 40.0, 0.15, 5, 200.0, "Mild Steel", "Carbide")

    assert isinstance(result, CalculationResult)
    assert result.error is None
    assert result.material_removal_rate is not None


@pytest.mark.parametrize(
    "fn,args",
    [
        (calculate_end_milling, (10.0, 2.0, 5.0, 0.05, 4, 100.0, "Nope", "Carbide")),
        (calculate_face_milling, (50.0, 1.5, 40.0, 0.15, 5, 200.0, "Nope", "Carbide")),
    ],
    ids=["end_milling", "face_milling"],
)
def test_error_result_shape(fn, args):
    result = fn(*args)

    assert isinstance(result, CalculationResult)
    assert result.error is not None
    assert result.error.code and result.error.message
    assert result.material_removal_rate is None
    assert result.spindle_speed_rpm is None


# --- FR-014: static module-boundary assertion ---


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def _python_files(relative: str) -> list[Path]:
    files = sorted((_SRC / relative).rglob("*.py"))
    assert files, f"no source files found under {relative!r}"
    return files


@pytest.mark.parametrize(
    "package,forbidden",
    [
        ("processes/machining/milling", "mfgparams.processes.machining.drilling"),
        ("processes/machining/drilling", "mfgparams.processes.machining.milling"),
    ],
    ids=["milling_does_not_import_drilling", "drilling_does_not_import_milling"],
)
def test_operations_do_not_import_each_other(package, forbidden):
    offenders = {
        path.relative_to(_SRC).as_posix(): sorted(
            module for module in _imported_modules(path) if module.startswith(forbidden)
        )
        for path in _python_files(package)
    }
    offenders = {path: modules for path, modules in offenders.items() if modules}

    assert not offenders, f"FR-014 module boundary violated: {offenders}"


def test_operations_depend_only_on_shared_top_level_modules():
    """Anything an operation imports from the package must be a shared module."""

    for package in ("processes/machining/milling", "processes/machining/drilling"):
        own_prefix = f"mfgparams.{package.replace('/', '.')}"
        for path in _python_files(package):
            for module in _imported_modules(path):
                if not module.startswith("mfgparams."):
                    continue
                if module.startswith(own_prefix):
                    continue
                remainder = module[len("mfgparams.") :]
                assert "." not in remainder, (
                    f"{path.relative_to(_SRC)} imports {module}, which is neither its own "
                    "package nor a shared top-level module (FR-014, Constitution VI)"
                )


# --- FR-004: the operation-first namespace is gone, with no alias ---


@pytest.mark.parametrize(
    "module",
    [
        "mfgparams.operations",
        "mfgparams.operations.drilling",
        "mfgparams.operations.milling",
        "mfgparams.operations.milling.end_milling",
        "mfgparams.operations.milling.face_milling",
    ],
)
def test_old_operation_first_namespace_is_unreachable(module):
    """There is exactly one path to each calculation (FR-004).

    No alias, shim or deprecation period: nothing was ever published under the
    old paths, so the restructure took the clean break rather than carrying a
    compatibility layer. A future contributor re-adding one to "help" would
    make both paths live, which is what this test exists to prevent -- the
    companion static check (``tests/static/test_no_old_layout.py``) catches the
    same mistake at the file level.
    """

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module)
