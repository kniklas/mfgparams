"""Manufacturing processes, each grouping the operations performed under it.

The package is organised process-first: a *process* (machining, and later
turning, welding, joining, forming) contains its *operations*, and an
operation may contain sub-operations::

    mfgparams.processes.machining.drilling
    mfgparams.processes.machining.milling.end_milling
    mfgparams.processes.machining.milling.face_milling

Only ``machining`` has implemented operations today. Turning, welding,
joining and forming are deliberately absent rather than stubbed: adding one
attaches a sibling package here and edits nothing that already exists, which
is Constitution Principle VI (extensibility by design) applied to the
process layer.

Cross-cutting behaviour -- validation, unit conversion, the tool and material
registries, configuration loading, result and error models -- stays at the
package root and is shared by every process rather than duplicated per
process.
"""
