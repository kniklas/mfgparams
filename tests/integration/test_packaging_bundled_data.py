"""Packaging test: bundled TOML files ship inside a built wheel (T017;
quickstart.md Scenario 2).

Invokes ``python -m build`` and inspects the resulting wheel's namelist.

These assertions carry the ``packaging`` marker and run **once**, not once
per interpreter: CI's ``build`` job and ``tox -e packaging``. The
``test (3.x)`` matrix and tox's ``envlist`` deselect them (issue #75 P1.3).
They verify *packaging*, not Python-version compatibility, and were in the
matrix only by accident of file location — at the cost of four isolated,
network-touching ``python -m build`` runs inside *required*, merge-blocking
checks, and of making ``tox -p`` unsafe (issue #74). The ``build`` job is
equally required, so they still gate a merge.

``build`` is part of the ``test`` extra (which ``dev`` includes via
``mfgparams[test]``), so both places that run them have it installed — these
are not skipped in automation. The ``importorskip`` guard below is for the
remaining case, which moving out of the matrix does **not** remove: a bare
environment with neither extra installed, e.g. someone running ``pytest``
against a plain ``pip install -e .`` checkout.

That guard imports ``build.__main__`` specifically, not just ``build``:
running ``python -m build`` leaves a ``build/`` scratch directory at the repo
root (gitignored, but not cleaned up afterward) as a side effect, regardless
of ``--outdir``. On an interpreter where the real ``build`` package isn't
installed, Python's implicit namespace-package mechanism resolves
``import build`` to that stray directory instead of raising ``ImportError``
— which used to make ``pytest.importorskip("build")`` wrongly not skip, and
the test would then fail instead of being skipped
(specs/013-tox-multi-python-testing; found via `tox` erroring on every Python
version after a local `python -m build` run, back when `tox` installed an
extra that did not carry ``build``). A namespace package has no ``__main__``
submodule, so importing that specifically still raises ``ImportError`` and
skips correctly either way.
"""

from __future__ import annotations

import ast
import glob
import importlib.machinery
import inspect
import re
import shutil
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11
    import tomli as tomllib  # type: ignore[no-redef]

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# NOTE: the ``packaging`` marker goes on the two tests that actually build a
# wheel, NOT on this module. The other two tests here build nothing and run in
# microseconds, and one of them —
# ``test_stray_build_scratch_directory_does_not_fool_the_skip_guard`` —
# asserts PEP 420 implicit-namespace-package resolution, which is genuinely
# interpreter-dependent and so is exactly what the version matrix exists to
# check. Marking the module would have quietly narrowed it to whichever single
# interpreter runs the `build` job (code review finding).


def _build_wheel(outdir: Path) -> Path:
    """Build the project's wheel into ``outdir`` and return its path, skipping
    the calling test if the ``build`` package isn't importable.

    Clears ``<repo>/build/`` first. setuptools' ``build_py`` copies sources
    into that scratch tree but never prunes files it no longer copies, and
    ``bdist_wheel`` then archives ``build/lib`` wholesale — so anything left
    there by an earlier run is silently baked into the wheel. Verified
    directly: dropping a file into ``build/lib/mfgparams/data/`` and
    rebuilding puts it in the wheel's namelist. Without this, a locally
    renamed or removed data file would still satisfy the assertions below
    from the stale copy, while a clean CI checkout saw the real result —
    exactly the false green these tests exist to prevent (code review
    finding). Note this does **not** stop these tests leaving a ``build/``
    directory behind — ``python -m build`` recreates it on the very next
    line — so the namespace-package shadowing the module docstring describes
    is still live, and ``importorskip("build.__main__")`` is still load-bearing.

    Note this uses `build`'s default *isolated* mode, which pip-installs the
    `[build-system].requires` backend into a throwaway environment — i.e. it
    touches the network. That is deliberate: it exercises the same path a real
    `pip install mfgparams` takes, which is the whole point of asserting on the
    wheel's contents. The cost is contained by building **once** per module
    rather than once per test (code review finding); the environment that runs
    these tests already had to reach PyPI to install `.[test]` in the first
    place, so this adds no new class of dependency.
    """
    pytest.importorskip("build.__main__")

    scratch = _REPO_ROOT / "build"
    shutil.rmtree(scratch, ignore_errors=True)
    # `ignore_errors` swallows a failed removal (a permission problem, or an
    # open handle on Windows), and a surviving tree is silently archived into
    # the wheel — the exact false green this call exists to prevent. Assert
    # rather than trust it (code review finding).
    assert not scratch.exists(), (
        f"could not clear the stale build scratch tree at {scratch}; "
        "a leftover build/lib would be archived into the wheel and could mask "
        "a packaging regression"
    )
    # `timeout` is generous because `build`'s isolated mode pip-installs the
    # `[build-system]` backend from PyPI: this runs inside the *required*
    # `build` check, where a transient registry slowdown tripping the timeout
    # would turn a merge-blocking check red for a reason unrelated to the
    # change under review. A local build takes ~3s (code review finding).
    # Since issue #75 P1.3 that is one check rather than four.
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(outdir)],
        # Explicit `cwd`, so the directory cleared above is the same one
        # setuptools writes to. Without it the build ran in pytest's cwd:
        # invoked from anywhere but the repo root it would either fail outright
        # ("does not appear to be a Python project") or clear one `build/` and
        # populate another, reinstating the stale-scratch false green
        # (code review finding).
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert (
        result.returncode == 0
    ), f"python -m build failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    wheels = sorted(glob.glob(str(outdir / "*.whl")))
    assert wheels, "expected python -m build to produce a wheel"
    return Path(wheels[0])


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory) -> Path:
    """One wheel build shared by every test in this module."""
    return _build_wheel(tmp_path_factory.mktemp("wheel"))


@pytest.mark.packaging
def test_wheel_contains_bundled_materials_and_tools_toml(built_wheel):
    """FR-015: every bundled data file ships, at its *full* in-wheel path.

    Asserted on the whole path, not a suffix. The suffixes these assertions
    originally used -- ``drilling/data/tools.toml`` and friends -- are exactly
    the part the process-namespace move left unchanged, so they would have kept
    passing even if ``[tool.setuptools.package-data]`` had never been
    repointed: the library would install, import fine from a source checkout,
    and fail only at first use of the installed wheel. That silent failure is
    the entire reason this test builds an artifact instead of reading the
    source tree.
    """
    names = set(zipfile.ZipFile(built_wheel).namelist())

    expected = {
        "mfgparams/data/materials.toml",
        "mfgparams/processes/machining/drilling/data/tools.toml",
        "mfgparams/processes/machining/milling/end_milling/data/tools.toml",
        "mfgparams/processes/machining/milling/face_milling/data/tools.toml",
    }
    missing = expected - names
    assert (
        not missing
    ), f"missing from the wheel: {sorted(missing)}\nwheel contained: {sorted(names)}"


@pytest.mark.packaging
def test_wheel_ships_no_data_under_the_old_operation_first_layout(built_wheel):
    """The negative half of FR-015: a stale glob left behind in
    ``package-data`` would keep passing the assertion above while shipping
    files nobody references."""
    stale = sorted(
        name for name in zipfile.ZipFile(built_wheel).namelist() if "mfgparams/operations/" in name
    )

    assert not stale, f"the wheel still carries the old layout: {stale}"


@pytest.mark.packaging
def test_packaged_materials_include_hardwood_softwood_and_engineered(built_wheel):
    wheel_path = built_wheel
    with zipfile.ZipFile(wheel_path) as archive:
        materials_file = next(
            name for name in archive.namelist() if name.endswith("data/materials.toml")
        )
        data = tomllib.loads(archive.read(materials_file).decode("utf-8"))

    names = [entry["name"] for entry in data["materials"]]
    for required in ("Oak", "Maple", "Pine", "Spruce", "Fir", "Plywood", "MDF"):
        assert required in names


def test_stray_build_scratch_directory_does_not_fool_the_skip_guard(tmp_path):
    """Regression test for the shadowing bug fixed in
    specs/013-tox-multi-python-testing: a `build/` directory with no
    `__init__.py` (exactly what `python -m build` leaves behind at the repo
    root) is resolved by Python as an implicit namespace package. Confirms
    that shape of "fake" `build` package satisfies a bare `import build` but
    not `import build.__main__` -- the actual property the two tests above
    rely on `pytest.importorskip("build.__main__")` to detect.

    Uses `importlib.machinery.PathFinder.find_spec` scoped to a `path=[...]`
    containing only the fake directory, rather than mutating `sys.path`/
    `sys.modules` on the real interpreter: this test's own process may have
    the genuine `build` package installed (dev-only tooling, present when
    running the full local suite), and per PEP 420 a regular package found
    anywhere on `sys.path` always wins over an earlier namespace-package
    candidate -- so a `sys.path`-based simulation wouldn't actually
    reproduce the bug on such an interpreter.
    """
    (tmp_path / "build").mkdir()

    spec = importlib.machinery.PathFinder.find_spec("build", path=[str(tmp_path)])
    assert spec is not None, "expected an implicit namespace package to be found"
    assert spec.origin is None, "expected a namespace package (no __init__.py, no origin file)"

    main_spec = importlib.machinery.PathFinder.find_spec(
        "build.__main__", path=spec.submodule_search_locations
    )
    assert main_spec is None, "a namespace package must not resolve build.__main__"


def _importorskip_arguments(func) -> list[str]:
    """Every constant argument passed to an ``importorskip(...)`` call inside
    ``func``, found by parsing the function rather than by matching source
    text.

    A substring check over `inspect.getsource` was the original
    implementation and is not semantic: it fails on a pure restyle (single
    quotes, a line break inside the call) while a mere *comment* containing
    the literal would satisfy it even if the real call had been reverted to
    the bare `"build"`. This mirrors the ast-based approach
    `tests/static/test_no_hardcoded_strings.py` already uses for the same
    shape of source-level guard (code review finding,
    specs/013-tox-multi-python-testing).
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    return [
        arg.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Attribute) and node.func.attr == "importorskip")
            or (isinstance(node.func, ast.Name) and node.func.id == "importorskip")
        )
        for arg in node.args
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
    ]


def test_packaging_tests_guard_against_build_dunder_main_not_bare_build():
    """Source-level guard: confirms `_build_wheel` -- the single place the two
    wheel-content tests above reach `python -m build` through -- still skips on
    `"build.__main__"`, not the bare `"build"` this file used before
    specs/013-tox-multi-python-testing. A plain string-literal revert wouldn't
    be caught by
    `test_stray_build_scratch_directory_does_not_fool_the_skip_guard` alone,
    since that test only proves the general mechanism, not that the real call
    site uses it.
    """
    arguments = _importorskip_arguments(_build_wheel)
    assert arguments == ["build.__main__"], (
        "_build_wheel must guard with "
        'pytest.importorskip("build.__main__"), not the bare "build" -- '
        f"found {arguments!r}"
    )


# --- Installation extras (FR-009, FR-010, FR-013) ---------------------------
#
# These assertions live in this module, rather than a file of their own, so
# they share its single `built_wheel` build. A second module would mean a
# second isolated `python -m build` -- another network round-trip inside the
# required `build` check -- to inspect metadata the first wheel already
# carries.


def _wheel_metadata(wheel: Path) -> list[str]:
    """Return the wheel's ``METADATA`` as a list of header lines."""
    with zipfile.ZipFile(wheel) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        return archive.read(name).decode("utf-8").splitlines()


#: The gating extra in a ``Requires-Dist`` marker. Shared with the guard in
#: ``mfgparams/__main__.py``, which parses the same field for the same reason:
#: quoting and spacing around ``==`` are not guaranteed, and older setuptools
#: emits single quotes. A fixed ``'extra == "'`` substring test would group
#: every console-gated requirement under ``None`` on such a wheel, emptying
#: ``grouped["all"]`` and failing the assertions below with a message blaming
#: `pyproject.toml` rather than the parser.
_EXTRA_MARKER = re.compile(r"""extra\s*==\s*['"]([^'"]+)['"]""")


def _requirements_by_extra(wheel: Path) -> dict[str | None, set[str]]:
    """Group the wheel's ``Requires-Dist`` entries by the extra that gates them.

    ``None`` is the default install -- what ``pip install mfgparams`` pulls in
    with no extras requested.
    """
    grouped: dict[str | None, set[str]] = {}
    for line in _wheel_metadata(wheel):
        if not line.startswith("Requires-Dist:"):
            continue
        value = line.split(":", 1)[1].strip()
        requirement, _, marker = value.partition(";")
        found = _EXTRA_MARKER.search(marker)
        grouped.setdefault(found.group(1) if found else None, set()).add(requirement.strip())
    return grouped


def _referenced_extras(requirements: set[str]) -> set[str]:
    """The extras named by ``mfgparams[...]`` self-references in ``requirements``.

    Parsed rather than substring-matched: asking whether the word "console"
    appears anywhere in the joined requirements also passes on a third-party
    `console-tools`, so it would keep passing after the aggregation it exists
    to prove had been removed.
    """
    referenced: set[str] = set()
    for requirement in requirements:
        name, bracket, rest = requirement.replace(" ", "").partition("[")
        if bracket and name == "mfgparams":
            referenced |= set(rest.split("]", 1)[0].split(","))
    return referenced


#: Declared extras that are deliberately outside `all`. `all` itself would be
#: self-referential, and `test`/`dev` are development toolchains -- `all` must
#: never pull tooling into a user install. Add a new *development* extra here;
#: a new *runtime* extra belongs in `all` instead. See
#: `test_all_extra_is_a_superset_of_every_runtime_extra` for why the split
#: cannot be derived from the wheel.
_NOT_RUNTIME_EXTRAS = frozenset({"all", "test", "dev"})


def _declared_extras(wheel: Path) -> set[str]:
    """Every extra the wheel declares, from its ``Provides-Extra`` lines."""
    return {
        line.split(":", 1)[1].strip()
        for line in _wheel_metadata(wheel)
        if line.startswith("Provides-Extra:")
    }


@pytest.mark.packaging
def test_wheel_declares_the_console_and_all_extras(built_wheel):
    """FR-010: both extras are declared, so users can ask for them by name."""
    provided = _declared_extras(built_wheel)

    assert {"console", "all"} <= provided, f"declared extras were {sorted(provided)}"


@pytest.mark.packaging
def test_default_install_pulls_in_no_console_only_dependency(built_wheel):
    """FR-009, FR-013: `pip install mfgparams` carries only what the
    calculations need.

    Written as a set *difference* rather than a fixed list, so it keeps its
    teeth once the console extra is no longer empty: the day a dependency is
    added to `[console]`, this fails if it also leaks into the default set.
    """
    grouped = _requirements_by_extra(built_wheel)
    default = grouped.get(None, set())
    console_only = grouped.get("console", set())

    leaked = default & console_only
    assert not leaked, (
        f"{sorted(leaked)} is gated by the console extra yet also required by a "
        "default install, so `pip install mfgparams` would carry it (FR-013)"
    )
    assert all(
        requirement.startswith("tomli") for requirement in default
    ), f"unexpected default runtime dependency: {sorted(default)}"


@pytest.mark.packaging
def test_all_extra_is_a_superset_of_every_runtime_extra(built_wheel):
    """FR-010: `[all]` means "everything optional the project ships".

    Two separate claims, and the weaker one is the easy one to test. Referring
    to each extra by name rather than restating its contents means `all` cannot
    drift from what those extras *hold* -- but it does not make `all` grow by
    itself, and checking only that `console` is referenced would keep passing
    the day an `api` extra is added and `all` is left behind. So the list is
    checked against every runtime extra the wheel declares, which is what turns
    the omission into a build failure instead of an incomplete install.

    Which extras are *runtime* extras is a project decision that metadata does
    not record, so it has to be written down somewhere; `_NOT_RUNTIME_EXTRAS`
    is that somewhere. Deriving the rest from the wheel does not remove that
    list, it just makes the default safe: a newly declared extra counts as
    runtime until someone says otherwise, so the failure is a loud one either
    way rather than a silently incomplete `mfgparams[all]`.
    """
    grouped = _requirements_by_extra(built_wheel)
    everything = grouped.get("all", set())

    referenced = _referenced_extras(everything)

    assert (
        referenced
    ), f"the `all` extra must aggregate the others by reference, found {sorted(everything)}"

    # ...and *only* by reference. A requirement restated here rather than named
    # through its extra is the drift this arrangement exists to prevent, and it
    # would sail past every check below: it contributes no entry to `referenced`,
    # so it neither satisfies nor violates the coverage assertion.
    restated = {r for r in everything if not r.replace(" ", "").startswith("mfgparams[")}
    assert not restated, (
        f"`all` must name each extra rather than restate its contents; "
        f"{sorted(restated)} is spelled out and will drift from the extra it duplicates"
    )
    # Every declared extra except `all` itself and the development ones.
    runtime_extras = _declared_extras(built_wheel) - _NOT_RUNTIME_EXTRAS

    assert runtime_extras, "the wheel declares no runtime extra; `all` has nothing to aggregate"
    missing = runtime_extras - referenced
    assert not missing, (
        f"`all` omits the extra(s) {sorted(missing)}. Two remedies, and which one is "
        f"right depends on what the extra is for: add it to `all` in pyproject.toml if "
        f"it is a runtime capability users should get from `mfgparams[all]`, or add it "
        f"to `_NOT_RUNTIME_EXTRAS` in this file if it is development tooling that must "
        f"never reach a user install. Declared runtime extras: {sorted(runtime_extras)}; "
        f"referenced by `all`: {sorted(referenced)}"
    )

    # Tooling named *directly* in `all` is already rejected by `restated` above
    # -- after it, every entry is an `mfgparams[...]` self-reference, so a
    # direct-name check against a list of tool names could never fire again and
    # would be a guard in name only. What is left to check is the reference
    # side, and it is checked transitively rather than here: see
    # `test_no_runtime_extra_reaches_the_development_toolchain`.


@pytest.mark.packaging
def test_no_runtime_extra_reaches_the_development_toolchain(built_wheel):
    """`all` must not reach `dev`/`test` *through* another extra either.

    The superset test above checks only what `all` names directly, so
    `console = ["mfgparams[dev]"]` leaves every one of its assertions green
    while `pip install mfgparams[all]` -- and `pip install mfgparams[console]`
    -- installs ruff, black, mypy, sphinx, bandit and pytest. Verified: with
    that line in `pyproject.toml`, the whole extras suite still passed.

    So the closure is walked rather than the first hop. A development extra
    reachable from `all` by any path is the same failure at any depth.
    """
    grouped = _requirements_by_extra(built_wheel)
    development = _NOT_RUNTIME_EXTRAS - {"all"}

    reached: set[str] = set()
    pending = ["all"]
    while pending:
        for extra in _referenced_extras(grouped.get(pending.pop(), set())):
            if extra not in reached:
                reached.add(extra)
                pending.append(extra)

    offending = reached & development
    assert not offending, (
        f"`mfgparams[all]` reaches the development extra(s) {sorted(offending)} through "
        f"{sorted(reached)}; `all` covers runtime extras only and must never pull tooling "
        f"into a user install"
    )


@pytest.mark.packaging
def test_the_all_extra_is_not_gated_by_an_environment_marker(built_wheel):
    """A marker on `all`'s self-references can empty the aggregate silently.

    `_requirements_by_extra` reads the `extra ==` clause and discards the rest
    of the marker, so `all = ["mfgparams[console]; python_version < '2.0'"]`
    satisfies every assertion above while `pip install mfgparams[all]` resolves
    to nothing on any interpreter. `all` is a pure aggregate; a condition on it
    belongs on the extra being aggregated, where it is visible.
    """
    conditional = []
    for line in _wheel_metadata(built_wheel):
        if not line.startswith("Requires-Dist:"):
            continue
        requirement, _, marker = line.split(":", 1)[1].strip().partition(";")
        found = _EXTRA_MARKER.search(marker)
        if not found or found.group(1) != "all":
            continue
        # `str.strip("and")` would strip the *characters* a/n/d, which quietly
        # empties a leftover bare `and` -- exactly what a second `extra ==`
        # clause leaves behind, and that is a case this test must catch.
        remainder = re.sub(r"^\s*and\b|\band\s*$", "", _EXTRA_MARKER.sub("", marker)).strip()
        if remainder:
            conditional.append(f"{requirement.strip()} ;{marker.strip()}")

    assert not conditional, (
        f"`all` carries the extra condition(s) {conditional}; a marker here can make the "
        f"aggregate resolve to nothing without failing any coverage check. Put the "
        f"condition on the aggregated extra's own requirements instead"
    )
