"""Shared, operation-agnostic data structures.

These types are used by every `mfgparams.processes.*` calculation module and by
the console layer. See
``specs/001-metal-drilling-calc/data-model.md`` for the authoritative field
definitions this module implements.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class UnitSystem(Enum):
    """Selects the unit system used for calculation input/output.

    Attributes:
        METRIC: Diameter/depth in mm, feed rate in mm/min, torque in N*m,
            power in kW. Spindle speed (RPM) and machining time (minutes)
            are unit-system independent.
        IMPERIAL: Diameter/depth in inches, feed rate in in/min, torque in
            in-lb, power in HP. Spindle speed (RPM) and machining time
            (minutes) are unit-system independent.
    """

    METRIC = "metric"
    IMPERIAL = "imperial"


class CalculationMode(Enum):
    """Selects which of the three ways a drilling calculation is performed.

    See ``specs/002-constrained-calculation-modes/data-model.md`` for the
    authoritative definition.

    Attributes:
        STANDARD: Spindle speed derived from material/tool reference
            values (the only mode in ``001-metal-drilling-calc``). Default;
            existing callers that never set ``mode`` get this behavior
            unchanged (SC-004).
        POWER_CONSTRAINED: Spindle speed reduced to fit a required
            ``available_power`` (FR-001, FR-002, FR-003, FR-004).
        FIXED_RPM: Spindle speed supplied directly via ``target_rpm``
            (FR-005, FR-006, FR-007, FR-008).
    """

    STANDARD = "standard"
    POWER_CONSTRAINED = "power-constrained"
    FIXED_RPM = "fixed-rpm"


class MachiningOperation(Enum):
    """The top-level machining operation the user selects in the REPL.

    Drives CLI dispatch only (specs/009-milling-calculations FR-001); it is
    not an input to any calculation function. Each member routes to its own
    ``mfgparams.processes.machining.<operation>`` package.

    Attributes:
        DRILLING: The existing drilling flow
            (``processes.machining.drilling``), unchanged by the
            introduction of this enum (FR-002).
        MILLING: The milling flow, which prompts for a
            :class:`MillingSubOperation` before any material/tool prompt.
    """

    DRILLING = "drilling"
    MILLING = "milling"


class MillingSubOperation(Enum):
    """The milling sub-operation selected after choosing milling.

    Drives CLI dispatch only (specs/009-milling-calculations FR-003).
    Each member routes to its own sibling package under
    ``mfgparams.processes.machining.milling`` with its own tool registry, input
    labelling and validation.

    Attributes:
        END_MILLING: Peripheral/slotting/pocketing work; the radial
            engagement input is labelled "radial depth of cut".
        FACE_MILLING: Surfacing work; the radial engagement input is
            labelled "width of cut".
    """

    END_MILLING = "end-milling"
    FACE_MILLING = "face-milling"


@dataclass(frozen=True)
class ErrorInfo:
    """A structured, machine-readable validation/error result.

    Attributes:
        code: Machine-readable identifier, e.g. ``"INVALID_DIAMETER"``,
            ``"INVALID_DEPTH"``, ``"MISSING_MATERIAL"``, ``"MISSING_TOOL"``,
            ``"UNSUPPORTED_COMBINATION"``.
        message: Human-readable explanation suitable for CLI display.
    """

    code: str
    message: str


@dataclass(frozen=True)
class CalculationResult:
    """The structured result returned by every operation's ``calculate()``.

    Field names are intentionally unit-agnostic; the ``unit_system`` field
    indicates which units apply to each numeric field:

    - ``spindle_speed_rpm``: RPM. Identical under METRIC and IMPERIAL (not a
      unit-system-dependent quantity).
    - ``feed_rate``: mm/min under METRIC, in/min under IMPERIAL.
    - ``machining_time``: Minutes (fractional). Identical under METRIC and
      IMPERIAL per the spec clarification (machining time is always reported
      in minutes regardless of unit system).
    - ``torque``: N*m under METRIC, in-lb under IMPERIAL.
    - ``power_required``: kW under METRIC, HP under IMPERIAL.
    - ``material_removal_rate``: cm^3/min under METRIC, in^3/min under
      IMPERIAL. ``None`` for operations that do not report it (drilling).

    When ``error`` is set, all numeric fields above MUST be ``None`` — this
    type is always returned, never raised, for expected validation failures
    (FR-015).

    Attributes:
        mode: Which calculation mode produced this result (FR-012 of
            ``002-constrained-calculation-modes``). Always set, including
            on error results (mirrors the requested mode). Defaults to
            ``CalculationMode.STANDARD`` for backward compatibility with
            ``001-metal-drilling-calc`` construction sites.
        material_removal_rate: Volumetric material removal rate (Q), in
            cm^3/min under METRIC and in^3/min under IMPERIAL
            (specs/009-milling-calculations research.md #7). Declared last,
            after every pre-existing field, so positional construction in
            existing drilling code and tests keeps working unchanged.
            Drilling results always leave this ``None``; milling results
            set it on success and leave it ``None`` on error.
    """

    spindle_speed_rpm: float | None
    feed_rate: float | None
    machining_time: float | None
    torque: float | None
    power_required: float | None
    unit_system: UnitSystem
    feasibility_warning: str | None = None
    error: ErrorInfo | None = None
    mode: CalculationMode = CalculationMode.STANDARD
    material_removal_rate: float | None = None
