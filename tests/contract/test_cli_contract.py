"""Contract test: cli.py must delegate all calculation logic to
mfgparams.calculate() and must not reimplement any drilling formulas
(T019).
"""

import ast
from pathlib import Path

CLI_PATH = Path(__file__).resolve().parents[2] / "src" / "mfgparams" / "cli.py"

# Formula-bearing operators/functions that would indicate the CLI is
# performing its own calculation instead of delegating to calculate().
DISALLOWED_CALL_NAMES = {"calculate_drilling_metrics", "pi", "sqrt"}


def test_cli_imports_calculate_from_public_api():
    tree = ast.parse(CLI_PATH.read_text())
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.name)
    assert "calculate" in imported_names, "cli.py must import calculate() from mfgparams"


def test_cli_does_not_import_formulas_module():
    tree = ast.parse(CLI_PATH.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = getattr(node, "module", None) or ""
            for alias in getattr(node, "names", []):
                full = f"{module}.{alias.name}" if module else alias.name
                assert "formulas" not in full, "cli.py must not import drilling formulas directly"


def test_cli_contains_no_disallowed_calculation_calls():
    tree = ast.parse(CLI_PATH.read_text())
    called_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.add(node.func.id)
    assert called_names.isdisjoint(DISALLOWED_CALL_NAMES)
