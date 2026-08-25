"""Bundled default materials/tools TOML package data (non-code).

See ``specs/005-configurable-materials-tools/research.md`` #2. This
``__init__.py`` exists only so ``importlib.resources.files()`` can resolve
this directory as a regular package under Python 3.9/3.10 (which do not
reliably support namespace-package resource resolution); it declares no
public API of its own.
"""
