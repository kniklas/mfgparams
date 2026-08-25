"""mfgparams: metal machining calculations library and interactive CLI.

Public surface (contracts/library-api.md)::

    from mfgparams import (
        calculate,
        list_material_types,
        list_materials,
        list_tools,
        UnitSystem,
    )

Materials are grouped into categories (``"metal"``, ``"wood"``, ...) that
drive the CLI's two-step type-then-material selection flow; see
``list_material_types`` and ``list_materials(material_type=...)``
(specs/008-material-categorization).

Exposes drilling calculations (``operations.drilling``) and milling
calculations (``operations.milling.end_milling`` and
``operations.milling.face_milling``, see
``specs/009-milling-calculations/contracts/library-api-milling.md``). Each
operation lives in its own ``mfgparams.operations.<operation>`` module per
Constitution Principle VI, so adding one never changes another's contract;
future operations (turning, ...) follow the same pattern.
"""

from __future__ import annotations

from mfgparams.models import (
    CalculationMode,
    CalculationResult,
    ErrorInfo,
    MachiningOperation,
    MillingSubOperation,
    UnitSystem,
)
from mfgparams.operations.drilling import calculate
from mfgparams.operations.drilling.tools import list_tools
from mfgparams.operations.milling.end_milling import (
    calculate_end_milling,
    list_end_mill_tools,
)
from mfgparams.operations.milling.face_milling import (
    calculate_face_milling,
    list_face_mill_tools,
)
from mfgparams.registry import list_material_types, list_materials

__all__ = [
    "calculate",
    "calculate_end_milling",
    "calculate_face_milling",
    "list_end_mill_tools",
    "list_face_mill_tools",
    "list_material_types",
    "list_materials",
    "list_tools",
    "UnitSystem",
    "CalculationMode",
    "CalculationResult",
    "ErrorInfo",
    "MachiningOperation",
    "MillingSubOperation",
]

__version__ = "0.4.0"
