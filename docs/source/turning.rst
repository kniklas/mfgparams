Turning calculations (user guide)
===================================

mfgparams calculates parameters for single-point-tool **turning** on a
lathe, alongside drilling and milling. This page covers using it from the
interactive text GUI; see :doc:`turning-api` for the library API.

Selecting an operation in the text GUI
---------------------------------------

Launch the text GUI with::

    mfgparams

A persistent menu bar stays visible at the top of the screen: **Exit**,
**Machining**, **Configuration**, **About**, **Help**. Selecting
**Machining** expands a tree in place, showing **Milling**, **Drilling**,
and **Turning** as flat leaves; selecting **Turning** opens its operation
screen directly, with no further tree-level expansion. It appears as a
centered, bordered floating window over the menu bar and tree (which stay
visible underneath, untouched): the left pane lists every turning input at
once (unit system, calculation mode, material type, material, turning
tool, workpiece diameter, depth of cut, length of cut, available power),
all simultaneously visible and editable; the right pane shows the live
result, updating automatically as you fill in or change an input.

**Up/Down** (or **j/k**) always moves to the next/previous field, regardless
of its type. A radio field (unit system, mode, material type, material,
tool) is always a single ``Label: value`` line — **Left/Right**/**h/l**/
**Space** cycle its value with wraparound and commit it immediately.
Numeric fields become editable the instant you select them; that text is
only written to the field once you navigate away from it, exactly as
described for drilling in :doc:`drilling`.

Turning inputs
----------------

After the unit system, calculation mode, material type, material and tool,
turning asks for three geometry values:

===========================  =========================================================
Prompt                       Meaning
===========================  =========================================================
Workpiece diameter            Diameter of the workpiece being turned, in mm / in.
Depth of cut                  Radial depth of material removed per pass, in mm / in.
Length of cut                 Length of the turning pass along the workpiece, in mm / in.
===========================  =========================================================

The depth of cut must be strictly less than half the workpiece diameter
(the workpiece radius) — a depth of cut at or beyond the radius is
physically impossible and is rejected with a clear error rather than
silently clamped.

Calculation modes
-----------------

Turning supports four calculation modes: ``standard``, ``power-constrained``,
and ``fixed-rpm`` behave identically to drilling's — see :doc:`drilling`'s
"Calculation modes" section for the full description; only the geometry
inputs above differ. Turning also has a fourth, turning-only mode:

**feed-rate-constrained**: instead of the feed rate per rotation being
derived from the selected material and turning tool, you supply it
directly — for example, to match a surface-finish requirement or a value
already dialed into the lathe. Selecting this mode shows a required
**Feed rate per rotation** field in place of the target-RPM field; spindle
speed is still derived exactly as in standard mode (from the material's
and tool's reference cutting speed and the entered diameter), but machining
time, cutting force, torque, and power are all recomputed from your
supplied feed rate instead of the material/tool's reference value. In the
text GUI, the **Feed rate per rotation** field nudges by a finer step than
every other field when you press **Left/Right**: 0.1 mm/rev under the
metric unit system, or 0.005 in/rev under imperial (rather than the 1
display-unit step every other numeric field uses).

Reading the results
--------------------

A turning result looks like this (40 mm diameter, 2 mm depth of cut, 100 mm
length of cut, Mild Steel, Carbide, standard mode)::

    Spindle speed:     477.5 RPM    (recommended)
    Feed rate:         100.3 mm/min
    Feed per rotation: 0.21 mm/rev
    Machining time:    1.00 min
    Torque:            16.0 N·m
    Power required:    0.80 kW
    Cutting force:     798.0 N

Spindle speed and feed rate describe how the workpiece is turned, machining
time is how long the pass takes, torque and power are what the spindle
needs to deliver, and cutting force is the tangential force the tool
experiences — the quantity a turning tool holder's rated force is
typically compared against. **Feed per rotation** expresses the same feed
rate as an amount of material advance per workpiece rotation (mm/rev or
in/rev) — the way feed rate is actually set on a lathe — alongside the
existing per-minute feed rate, whose own meaning and value are unchanged.
Turning does not report a material removal rate (that line is specific to
milling) but is the only process that reports cutting force and feed per
rotation, both of which stay ``None`` for drilling and milling results.

If you supply an available lathe/tool power and the calculated power
exceeds it, the result is still shown, with a warning line telling you the
cut is beyond what the machine can deliver.

Limits and validation
----------------------

Workpiece diameter, depth of cut, and length of cut are each validated as
part of the calculation itself: an out-of-range value produces a clear,
actionable error in the right pane rather than a result. The bounds
themselves are:

.. list-table::
   :header-rows: 1

   * - Setting
     - Default
     - Applies to
   * - ``max_turning_diameter_mm``
     - 500.0 mm
     - Workpiece diameter.
   * - ``max_turning_depth_of_cut_mm``
     - 10.0 mm
     - Depth of cut.
   * - ``max_turning_length_of_cut_mm``
     - 1000.0 mm
     - Length of cut.

These are distinct from drilling's and milling's own bounds (e.g.
``max_depth_of_cut_mm``, 50 mm) — a single-point turning tool's realistic
depth of cut per pass is far shallower than a milling cutter's, so the two
cannot share one bound. In addition, all three values must be positive,
finite, and within their bound; ``NaN``, ``+inf``/``-inf`` and non-numeric
values are all rejected before the bound is checked, the same posture
drilling and milling already apply (issue #56).

Library callers can override these bounds via ``calculate_turning()``'s
``config_path`` argument (see :doc:`turning-api`).

Assumptions
-----------

The turning model uses standard single-point turning formulas as published
in widely-referenced industry sources (Sandvik Coromant's "Machining
Formulas" reference and Machinery's Handbook — the same class of source
drilling's own formulas cite). Unlike drilling, turning's machining-time
formula has no point-engagement allowance term, since a single-point
turning tool has no drill-point geometry to account for. Only straight
(outside-diameter) turning is in scope; facing, grooving, parting,
threading, and taper turning are deliberately deferred to a later feature.
See ``specs/019-turning-calculations/research.md`` for the formulas and
their sources, and ``specs/020-turning-feed-per-rotation/research.md`` for
the feed-rate-constrained mode and feed-per-rotation reporting.
