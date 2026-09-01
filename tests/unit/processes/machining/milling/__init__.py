"""Test package marker: keeps same-named milling test modules distinct.

Without it, ``end_milling/test_tools_registry.py`` and
``face_milling/test_tools_registry.py`` (and their ``test_formulas.py``
counterparts, which also share a basename with drilling's) collide during
pytest collection, since this repository otherwise uses rootdir-relative
module names for tests.
"""
