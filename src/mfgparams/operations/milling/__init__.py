"""Milling operation package (specs/009-milling-calculations).

Groups the two milling sub-operations — :mod:`~mfgparams.operations.milling.end_milling`
and :mod:`~mfgparams.operations.milling.face_milling` — as siblings of
``operations.drilling`` per Constitution Principle VI. Each sub-operation
owns its own tool registry, bundled reference data, input labelling and
validation; both delegate their arithmetic to the shared
:mod:`~mfgparams.operations.milling._shared` formula core, which is
valid for both under the full/symmetric-engagement assumption
(research.md #2).
"""
