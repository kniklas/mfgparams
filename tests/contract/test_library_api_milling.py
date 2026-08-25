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
import inspect
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


@pytest.mark.parametrize(
    "name",
    [
        "calculate_end_milling",
        "calculate_face_milling",
        "list_end_mill_tools",
        "list_face_mill_tools",
    ],
)
def test_entry_point_is_importable_from_the_package_root(name):
    assert hasattr(mfgparams, name)
    assert name in mfgparams.__all__
    assert callable(getattr(mfgparams, name))


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
        ("operations/milling", "mfgparams.operations.drilling"),
        ("operations/drilling", "mfgparams.operations.milling"),
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

    for package in ("operations/milling", "operations/drilling"):
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
