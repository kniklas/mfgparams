"""Sphinx configuration for mfgparams documentation.

Minimal scaffold added alongside the CI `docs` job
(specs/003-ci-quality-security-gates) so that job has a real Sphinx project
to build against. Expand with autodoc/napoleon extensions and additional
pages as documentation content grows (see 001-metal-drilling-calc tasks.md
T035/T036 for the original documentation-content tasks).
"""

from __future__ import annotations

project = "mfgparams"
copyright = "2026, kniklas"
author = "kniklas"

extensions: list[str] = []

templates_path: list[str] = ["_templates"]
exclude_patterns: list[str] = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path: list[str] = []
