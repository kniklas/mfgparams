---
name: pypi-package-builder
description: 'Repo-specific skill for scaffolding, packaging, and publishing a Python distribution from this repository to PyPI. Use when asked to create a pip-installable package, set up pyproject.toml, add packaging/build config, version the package, set up PyPI publishing CI, or prepare a release. Follows this repo''s Python conventions in .github/instructions/python.instructions.md.'
---

# PyPI Package Builder (mfgparams)

Use this skill whenever the task is to turn (part of) this repository into a
publishable Python package, or to maintain/release an already-packaged one.
It complements `.github/instructions/python.instructions.md` — that file
governs code style; this skill governs packaging, versioning, and release.

Do not invent a tech stack. If this repo has not yet adopted Python as part
of its stack (check `.specify/memory/constitution.md` and `specs/`), confirm
with the user before scaffolding packaging files.

## 1. When to use this skill

Trigger on requests like: "create a pip package", "publish to PyPI", "set up
pyproject.toml", "add a build backend", "version this package", "set up a
release workflow", "make this installable via pip".

## 2. Package layout

Use the `src/` layout to avoid accidental imports of uninstalled code:

```
pyproject.toml
README.md
LICENSE
src/
  <import_name>/
    __init__.py
    py.typed
tests/
  test_<module>.py
```

- PyPI distribution name: lowercase with hyphens, e.g. `mfgparams`.
- Python import name: underscores, e.g. `mfgparams`.
- Include an empty `py.typed` marker file if the package ships type hints
  (per PEP 561) — required since `.github/instructions/python.instructions.md`
  mandates type hints on public APIs.

## 3. Build backend

Default to **hatchling** unless the user has a reason to prefer another
(e.g. an existing Poetry workflow):

- Hatchling: minimal config, no plugin lock-in, works well for simple
  libraries and CLI tools. Use this by default.
- Setuptools + `setuptools_scm`: use only if the user wants git-tag-derived
  versions and is already invested in setuptools.
- Poetry: use only if the user explicitly wants Poetry's dependency
  resolution/lockfile workflow.

Minimal `pyproject.toml` (hatchling, static versioning):

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mfgparams"
version = "0.1.0"
description = "TODO: one-line summary"
readme = "README.md"
requires-python = ">=3.10"
license = { text = "MIT" }
authors = [{ name = "TODO" }]
classifiers = [
  "Programming Language :: Python :: 3",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
]
dependencies = []

[project.optional-dependencies]
dev = ["pytest", "mypy", "ruff", "black"]

[tool.hatch.build.targets.wheel]
packages = ["src/mfgparams"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.mypy]
python_version = "3.10"
strict = true

[tool.ruff]
line-length = 88
```

If the package needs a CLI entry point, add:

```toml
[project.scripts]
mfgparams = "mfgparams.__main__:main"
```

## 4. Versioning

- Use [PEP 440](https://peps.python.org/pep-0440/)-compliant versions
  (`MAJOR.MINOR.PATCH`, e.g. `0.1.0`).
- Prefer **static versioning** in `pyproject.toml` for simplicity, bumped
  manually per release, unless the user wants dynamic git-tag versioning
  (`setuptools_scm` or hatch-vcs) — offer that only if asked.
- Follow [semantic versioning](https://semver.org/): breaking changes bump
  MAJOR, backward-compatible features bump MINOR, fixes bump PATCH.
- Before `1.0.0`, minor version bumps may include breaking changes; note
  this in the changelog.

## 5. Local build & validation checklist

Before publishing, verify locally:

```bash
python -m pip install --upgrade build twine
python -m build                 # produces dist/*.whl and dist/*.tar.gz
python -m twine check dist/*    # validates metadata/README rendering
pytest                          # tests pass
mypy src/                       # type checks pass (per .github/instructions/python.instructions.md)
ruff check .                    # lint passes
```

Do not proceed to publish if any of these fail.

## 6. Publishing to PyPI

Prefer **Trusted Publishing (OIDC)** over long-lived API tokens:

1. On PyPI, configure a Trusted Publisher for this GitHub repo/workflow.
2. Add a GitHub Actions workflow (e.g. `.github/workflows/publish.yml`) that
   builds the package and publishes on tagged releases using
   `pypa/gh-action-pypi-publish` with `id-token: write` permission — no
   secrets required.
3. Test against **TestPyPI** first for any new package or backend change.

Example release workflow trigger: push a tag matching `v*.*.*`, build with
`python -m build`, then publish via the trusted-publishing action.

## 7. Anti-patterns to avoid

- Publishing without running tests/lint/type-check first.
- Skipping the `src/` layout for new packages (flat layout risks import
  shadowing during tests).
- Hardcoding PyPI API tokens in CI secrets when Trusted Publishing is
  available.
- Bumping versions without updating a changelog entry.
- Reusing a PyPI package name without first checking availability at
  https://pypi.org/search/.
