"""Milling operation package (specs/009-milling-calculations).

Milling is an operation of the machining process, a sibling of
``processes.machining.drilling``. It keeps its own sub-operation level, so
:mod:`~mfgparams.processes.machining.milling.end_milling` and
:mod:`~mfgparams.processes.machining.milling.face_milling` sit *within* milling
rather than beside drilling, per Constitution Principle VI. Each sub-operation
owns its own tool registry, bundled reference data, input labelling and
validation; both delegate their arithmetic to the shared
:mod:`~mfgparams.processes.machining.milling._shared` formula core, which is
valid for both under the full/symmetric-engagement assumption
(research.md #2).
"""
