"""Machining: material removal by a rotating cutting tool.

Operation registry/dispatch for the machining process. Its implemented
operations are :mod:`~mfgparams.processes.machining.drilling` and
:mod:`~mfgparams.processes.machining.milling`; milling keeps its own
sub-operation level, so end milling and face milling sit *within* milling
rather than beside drilling::

    machining/
        drilling/
        milling/
            end_milling/
            face_milling/

Currently empty as a module: both operations are imported directly by
``mfgparams/__init__.py``, which is the public surface. A further machining
operation (boring, reaming, tapping) registers alongside them here per
Constitution Principle VI, and a further *process* attaches beside
``machining`` under :mod:`mfgparams.processes` without editing this package.
"""
