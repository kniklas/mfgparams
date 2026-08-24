"""Shared input validation (FR-009, FR-010, FR-018).

All validation returns :class:`~machine_calc.models.ErrorInfo` rather than
raising exceptions, per FR-015. Bounds are always expressed and checked in
canonical metric units (mm); callers convert imperial input to metric before
calling these functions.

All error messages are sourced from the message catalog (FR-019a-e) via
:mod:`machine_calc.i18n`; the optional ``locale`` parameter defaults to
English (T033a).
"""

from __future__ import annotations

import math

from machine_calc.config import Configuration
from machine_calc.i18n import DEFAULT_LOCALE, translate
from machine_calc.models import CalculationMode, ErrorInfo


def _is_positive_finite_number(value: object) -> bool:
    """Return ``True`` when ``value`` is a positive, finite, non-bool number.

    Shared guard for every dimensional validator in this module: zero,
    negative, non-numeric, ``None``, ``bool``, ``NaN`` and ``Infinity`` are
    all rejected (specs/009-milling-calculations FR-008), the posture first
    established by :func:`validate_target_rpm`. Drilling's diameter/depth
    validators route through it too, so that a ``NaN`` — for which both
    ``value <= 0`` and ``value > maximum`` are ``False`` — cannot slip past
    the bound checks and poison the calculation (issue #56), and so that a
    non-numeric value returns an ``ErrorInfo`` instead of raising
    ``TypeError`` from the comparison, per the never-raises contract
    (FR-015).
    """

    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and value > 0


def validate_diameter_mm(
    diameter_mm: float, config: Configuration, locale: str = DEFAULT_LOCALE
) -> ErrorInfo | None:
    """Validate a drill diameter (in mm) against positivity and bounds.

    ``NaN``, ``Infinity``, ``None``, ``bool`` and non-numeric values are
    rejected up front by :func:`_is_positive_finite_number` rather than
    being compared against the bounds, so they cannot pass validation
    (issue #56) or raise from the comparison.
    """

    if not _is_positive_finite_number(diameter_mm):
        return ErrorInfo("INVALID_DIAMETER", translate(locale, "error.invalid_diameter.zero"))
    if diameter_mm > config.max_diameter_mm:
        return ErrorInfo(
            "INVALID_DIAMETER",
            translate(
                locale,
                "error.invalid_diameter.max",
                max_diameter_mm=config.max_diameter_mm,
            ),
        )
    return None


def validate_depth_mm(
    depth_mm: float, config: Configuration, locale: str = DEFAULT_LOCALE
) -> ErrorInfo | None:
    """Validate a hole depth (in mm) against positivity and bounds.

    Applies the same non-finite/non-numeric rejection as
    :func:`validate_diameter_mm` (issue #56).
    """

    if not _is_positive_finite_number(depth_mm):
        return ErrorInfo("INVALID_DEPTH", translate(locale, "error.invalid_depth.zero"))
    if depth_mm > config.max_depth_mm:
        return ErrorInfo(
            "INVALID_DEPTH",
            translate(locale, "error.invalid_depth.max", max_depth_mm=config.max_depth_mm),
        )
    return None


def validate_material_present(
    material: str | None, locale: str = DEFAULT_LOCALE
) -> ErrorInfo | None:
    """Validate that a material name was supplied (non-empty)."""

    if not material:
        return ErrorInfo("MISSING_MATERIAL", translate(locale, "error.missing_material"))
    return None


def validate_tool_present(tool: str | None, locale: str = DEFAULT_LOCALE) -> ErrorInfo | None:
    """Validate that a drilling tool name was supplied (non-empty)."""

    if not tool:
        return ErrorInfo("MISSING_TOOL", translate(locale, "error.missing_tool"))
    return None


def validate_depth_of_cut_mm(
    depth_of_cut_mm: float,
    config: Configuration,
    locale: str = DEFAULT_LOCALE,
    label_key: str = "cli.label.axial_depth_of_cut",
) -> ErrorInfo | None:
    """Validate a milling depth of cut (in mm) — axial, radial, or width.

    Args:
        depth_of_cut_mm: The depth/width, in canonical metric mm.
        config: Supplies ``max_depth_of_cut_mm`` (FR-018).
        locale: Message-catalog locale for the returned message.
        label_key: Catalog key naming which input is being validated, so
            the message can distinguish an axial depth of cut from a radial
            depth of cut or a width of cut (Constitution VIII — the label
            itself comes from the catalog, never a literal).

    Returns:
        ``None`` when valid, else an ``INVALID_DEPTH_OF_CUT``
        :class:`~machine_calc.models.ErrorInfo`.
    """

    label = translate(locale, label_key)
    if not _is_positive_finite_number(depth_of_cut_mm):
        return ErrorInfo(
            "INVALID_DEPTH_OF_CUT",
            translate(locale, "error.invalid_depth_of_cut.zero", label=label),
        )
    if depth_of_cut_mm > config.max_depth_of_cut_mm:
        return ErrorInfo(
            "INVALID_DEPTH_OF_CUT",
            translate(
                locale,
                "error.invalid_depth_of_cut.max",
                label=label,
                max_depth_of_cut_mm=config.max_depth_of_cut_mm,
            ),
        )
    return None


def validate_engagement_mm(
    radial_engagement_mm: float,
    diameter_mm: float,
    locale: str = DEFAULT_LOCALE,
    label_key: str = "cli.label.radial_depth_of_cut",
) -> ErrorInfo | None:
    """Validate that radial engagement does not exceed the cutter diameter.

    Implements FR-009: a radial depth of cut (end milling) or width of cut
    (face milling) larger than the tool/cutter diameter is geometrically
    impossible, so it is rejected rather than silently clamped. Positivity
    and upper-bound checks belong to :func:`validate_depth_of_cut_mm` and
    are expected to have run first (data-model.md "Validation Order").
    """

    if not _is_positive_finite_number(radial_engagement_mm) or not _is_positive_finite_number(
        diameter_mm
    ):
        return None
    if radial_engagement_mm > diameter_mm:
        return ErrorInfo(
            "INVALID_ENGAGEMENT",
            translate(
                locale,
                "error.invalid_engagement",
                label=translate(locale, label_key),
                diameter_mm=diameter_mm,
            ),
        )
    return None


def validate_feed_per_tooth_mm(
    feed_per_tooth_mm: float, locale: str = DEFAULT_LOCALE
) -> ErrorInfo | None:
    """Validate a milling feed per tooth (chip load), in mm/tooth (FR-008).

    No upper bound is applied — feed per tooth is bounded in practice by
    the depth-of-cut and diameter limits it is multiplied against, and the
    spec defines configurable maxima only for diameter, depth/width and
    length of cut (FR-018). An extreme-but-otherwise-valid value that would
    overflow a downstream calculation (e.g. ``feed_rate_mm_min = rpm *
    feed_per_tooth_mm * number_of_teeth``) is instead rejected post-hoc as
    ``CALCULATION_OVERFLOW`` by
    ``operations.milling._calculate._reject_if_overflowed()``, rather than
    being bounded here.
    """

    if not _is_positive_finite_number(feed_per_tooth_mm):
        return ErrorInfo(
            "INVALID_FEED_PER_TOOTH", translate(locale, "error.invalid_feed_per_tooth")
        )
    return None


def validate_tooth_count(number_of_teeth: float, locale: str = DEFAULT_LOCALE) -> ErrorInfo | None:
    """Validate a cutter's number of teeth/flutes/inserts (FR-008).

    Accepts int-valued floats (``4.0``) for caller convenience but rejects
    a fractional count such as ``4.5``: a cutter cannot have a fractional
    number of teeth.
    """

    if not _is_positive_finite_number(number_of_teeth):
        return ErrorInfo("INVALID_TOOTH_COUNT", translate(locale, "error.invalid_tooth_count"))
    if float(number_of_teeth) != int(number_of_teeth):
        return ErrorInfo(
            "INVALID_TOOTH_COUNT", translate(locale, "error.invalid_tooth_count.fractional")
        )
    return None


def validate_length_of_cut_mm(
    length_of_cut_mm: float, config: Configuration, locale: str = DEFAULT_LOCALE
) -> ErrorInfo | None:
    """Validate a milling length of cut (travel distance), in mm (FR-008, FR-018)."""

    if not _is_positive_finite_number(length_of_cut_mm):
        return ErrorInfo(
            "INVALID_LENGTH_OF_CUT", translate(locale, "error.invalid_length_of_cut.zero")
        )
    if length_of_cut_mm > config.max_length_of_cut_mm:
        return ErrorInfo(
            "INVALID_LENGTH_OF_CUT",
            translate(
                locale,
                "error.invalid_length_of_cut.max",
                max_length_of_cut_mm=config.max_length_of_cut_mm,
            ),
        )
    return None


def validate_mill_diameter_mm(
    diameter_mm: float, config: Configuration, locale: str = DEFAULT_LOCALE
) -> ErrorInfo | None:
    """Validate an end-mill/face-mill cutter diameter (in mm).

    Reuses drilling's ``INVALID_DIAMETER`` code (data-model.md "New Error
    Codes") but checks the milling-specific ``max_mill_diameter_mm`` bound
    rather than drilling's ``max_diameter_mm`` (FR-018).
    """

    if not _is_positive_finite_number(diameter_mm):
        return ErrorInfo("INVALID_DIAMETER", translate(locale, "error.invalid_mill_diameter.zero"))
    if diameter_mm > config.max_mill_diameter_mm:
        return ErrorInfo(
            "INVALID_DIAMETER",
            translate(
                locale,
                "error.invalid_mill_diameter.max",
                max_mill_diameter_mm=config.max_mill_diameter_mm,
            ),
        )
    return None


def validate_mill_tool_present(tool: str | None, locale: str = DEFAULT_LOCALE) -> ErrorInfo | None:
    """Validate that a milling tool name was supplied (non-empty).

    Mirrors :func:`validate_tool_present` but uses the milling wording, since
    drilling's catalog entry names a *drilling* tool (FR-019a).
    """

    if not tool:
        return ErrorInfo("MISSING_TOOL", translate(locale, "error.missing_mill_tool"))
    return None


def validate_target_rpm(target_rpm: float | None, locale: str = DEFAULT_LOCALE) -> ErrorInfo | None:
    """Validate a supplied target spindle RPM (fixed-RPM mode, FR-007).

    ``target_rpm`` MUST be a positive, finite number. Zero, negative,
    non-numeric, ``NaN``, and ``Infinity`` values are all rejected under
    the same ``INVALID_TARGET_RPM`` code (spec.md Clarifications
    2026-07-11) — the same validation posture as diameter/depth in the
    base drilling spec. No additional maximum/minimum range validation or
    clamping is applied beyond finiteness and positivity (spec.md
    Clarifications 2026-07-11 second checklist follow-up); a ``None``
    value (not supplied) is not an error here — callers decide whether a
    missing ``target_rpm`` is itself an error (e.g. required in fixed-RPM
    mode) via :func:`validate_mode_arguments`.
    """

    if target_rpm is None:
        return None
    if not isinstance(target_rpm, (int, float)) or isinstance(target_rpm, bool):
        return ErrorInfo("INVALID_TARGET_RPM", translate(locale, "error.invalid_target_rpm"))
    if not math.isfinite(target_rpm) or target_rpm <= 0:
        return ErrorInfo("INVALID_TARGET_RPM", translate(locale, "error.invalid_target_rpm"))
    return None


def validate_mode_arguments(
    mode: CalculationMode,
    available_power: float | None,
    target_rpm: float | None,
    locale: str = DEFAULT_LOCALE,
) -> ErrorInfo | None:
    """Validate mode/target_rpm/available_power mutual-exclusivity (FR-009).

    The supplied ``mode`` is authoritative (spec.md FR-009, Clarifications
    2026-07-11 second checklist follow-up):

    - ``CalculationMode.STANDARD`` (the default) ignores any supplied
      ``target_rpm`` — never a conflict. A supplied ``available_power`` is
      only used for an advisory feasibility warning, but is still
      type/finiteness-checked (``INVALID_AVAILABLE_POWER``) so a
      non-numeric or non-finite value can't reach a downstream conversion
      or comparison and raise.
    - ``CalculationMode.POWER_CONSTRAINED`` requires ``available_power`` to
      be supplied, and rejects a request that also supplies ``target_rpm``
      (power-constrained mode derives spindle speed; it does not accept
      one directly) — both cases are ``MODE_CONFLICT``. An invalid
      (non-numeric, non-finite, zero, or negative) ``available_power`` is
      ``INFEASIBLE_POWER_BUDGET`` since no spindle speed could ever meet
      it.
    - ``CalculationMode.FIXED_RPM`` requires ``target_rpm`` to be supplied;
      a missing ``target_rpm`` in this mode is reported as
      ``INVALID_TARGET_RPM`` (FR-007) by the caller, not here.
      ``available_power`` remains optional/advisory in this mode (FR-008)
      and is never a conflict, but — like ``STANDARD`` — is still
      type/finiteness-checked (``INVALID_AVAILABLE_POWER``).
    """

    if mode is CalculationMode.STANDARD:
        return _validate_advisory_available_power(available_power, locale)

    if mode is CalculationMode.POWER_CONSTRAINED:
        if target_rpm is not None:
            return ErrorInfo("MODE_CONFLICT", translate(locale, "error.mode_conflict"))
        if available_power is None:
            return ErrorInfo("MODE_CONFLICT", translate(locale, "error.mode_conflict"))
        if not _is_positive_finite_number(available_power):
            # A supplied-but-invalid budget (non-numeric, bool, non-finite,
            # zero, or negative) is presence-wise satisfied but can never
            # be met by any spindle speed, so it is reported as the same
            # INFEASIBLE_POWER_BUDGET the downstream <= 0 checks in
            # drilling's/milling's _compute_metrics() already use for a
            # non-positive budget — rather than reaching hp_to_kw() or a
            # numeric comparison downstream and raising TypeError, which
            # would violate the public API's never-raises contract.
            return ErrorInfo(
                "INFEASIBLE_POWER_BUDGET", translate(locale, "error.infeasible_power_budget")
            )
        return None

    # mode is CalculationMode.FIXED_RPM
    return _validate_advisory_available_power(available_power, locale)


def _validate_advisory_available_power(
    available_power: float | None, locale: str
) -> ErrorInfo | None:
    """Type/finiteness-check an ``available_power`` that is only used
    advisory-side (STANDARD and FIXED_RPM modes' optional feasibility
    warning, built in ``_build_result()``).

    Unlike ``POWER_CONSTRAINED``'s hard budget, an invalid value here has
    no ``INFEASIBLE_POWER_BUDGET`` interpretation — there is no spindle
    speed being solved for — but left unchecked it would reach
    ``hp_to_kw()`` (imperial) or a numeric comparison against
    ``metrics.power_kw`` (metric) downstream and raise ``TypeError`` for a
    non-numeric value, violating the "never raises" API contract
    (FR-012/FR-015). ``None`` (not supplied) is always valid.
    """

    if available_power is None or _is_positive_finite_number(available_power):
        return None
    return ErrorInfo("INVALID_AVAILABLE_POWER", translate(locale, "error.invalid_available_power"))
