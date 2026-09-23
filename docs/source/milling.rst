Milling calculations (user guide)
=================================

mfgparams calculates parameters for two milling sub-operations —
**end milling** and **face milling** — alongside drilling. This page covers
using them from the interactive text GUI; see :doc:`milling-api` for the
library API.

Selecting an operation in the text GUI
---------------------------------------

Launch the text GUI with::

    mfgparams

A persistent menu bar stays visible at the top of the screen: **Exit**,
**Machining**, **Configuration**, **About**, **Help**. Selecting
**Machining** expands a tree in place, showing **Milling** and
**Drilling** as flat leaves; selecting **Milling** opens its operation
screen directly. It appears as a centered, bordered floating window over
the menu bar and tree (which stay visible underneath, untouched): the left
pane lists every milling input at once — the sub-operation choice (**end
milling** or **face milling**), unit system, calculation mode, material
type, material, and the appropriate tool (end-mill or face-mill), plus the
geometry fields below — all simultaneously visible and editable, with no
separate screen per field; the right pane shows the live result, updating
automatically as you fill in or change an input. Changing the sub-operation
choice switches which set of remembered answers the rest of the screen
shows, without closing and reopening it. Selecting **Drilling** from the
tree instead leads to the flow described in :doc:`drilling`.

**Up/Down** (or **j/k**) always moves to the next/previous field, regardless
of its type. A radio field (sub-operation, unit system, mode, material
type, material, tool) is always a single ``Label: value`` line —
**Left/Right**/**h/l**/**Space** cycle its value with wraparound and commit
it immediately, with no separate confirm step. Once **metal** is chosen as
the material type, the Material field also opens a dedicated selection
window on **Enter**, on top of that ordinary cycling — see `Selecting a
metal material`_ below. Numeric fields become editable the instant you
select them — start typing a digit (or ``.``/``-``) and it edits the
field's buffer immediately, no separate "start editing" step; Left/Right
nudges the buffer up or down by a small step (1 display unit for most
fields). **Feed per tooth** nudges by a finer step than the rest: 0.1
mm/tooth under the metric unit system, or 0.001 in/tooth under imperial —
a standard chip-load shop-practice increment, not a literal conversion of
the metric value — for either sub-operation. Backspace removes the last
character. That text is only written to the field once you navigate away
from it (Up/Down) — text that still doesn't parse as a number at that
point is discarded (the field keeps its last valid value) and a message
appears in the status bar beneath both panes until you correct it.

Pressing Escape moves focus back to the menu bar without closing the open
screen; pressing Escape again, from the menu bar, closes it and returns to
the menu bar/tree, letting you start another calculation without leaving
the text GUI. Each operation (and each milling sub-operation) remembers its
*own* previous answers as defaults for the rest of the session, so
switching from end milling to drilling and back does not lose your milling
inputs.

Selecting a metal material
---------------------------

Once **metal** is chosen as the material type, the Material field still
cycles one material at a time with **Left/Right**/**h/l**/**Space**, exactly
like any other radio field — but pressing **Enter** on it instead opens a
centered selection window for finding a material by more than just cycling
through the list. It lists every metal material in three columns — common
name, EN material number (e.g. ``1.0038``), and shortened/DIN-style
designation (e.g. ``S235JR``) — with an independent search field for each
column; a material missing a recorded number/designation shows that cell
blank. **Tab**/**Right** and **Shift+Tab**/**Left** switch which column's
search field receives typed characters, without losing text already typed
into the others; typing narrows the list to materials matching *every*
non-empty search across all three columns at once. **Up**/**Down** move the
highlighted row; **Enter** selects the highlighted material and closes the
window; **Escape** closes it without changing the current selection.
Reopening the window always starts with the material you already had
selected (if any) highlighted, and every search field cleared. This
behaves identically to :doc:`drilling`'s own Material field (same columns,
search, navigation, and confirm/cancel keys), for either sub-operation —
see that page's own "Selecting a metal material" section, or
``specs/023-material-selector-dialog/contracts/materials-config-schema-delta.md``,
for the materials-config schema that populates the extra two columns.
Non-metal material types are unaffected and only ever offer the ordinary
Left/Right/Space radio-cycling behavior, with no selection window.

End milling inputs
------------------

After the unit system, material type, material and tool, end milling asks for
six geometry values:

===========================  =========================================================
Prompt                       Meaning
===========================  =========================================================
Cutter diameter              Diameter of the end mill (mm / in).
Axial depth of cut           Depth the cutter is stepped down into the workpiece
                             (a\ :sub:`p`), in mm / in.
Radial depth of cut          Sideways engagement into the material (a\ :sub:`e`), in
                             mm / in. Must not exceed the cutter diameter.
Feed per tooth               Chip load per cutting edge (f\ :sub:`z`), in mm/tooth or
                             in/tooth.
Number of teeth              Number of cutting edges on the cutter (a whole number).
Length of cut                Total distance the cutter travels through the cut, in
                             mm / in. This drives the machining time.
===========================  =========================================================

Face milling inputs
-------------------

Face milling asks the same six values, except that **radial depth of cut** is
replaced by **width of cut** — the width of the surface being faced, measured
across the cutter. As with end milling it must not exceed the cutter diameter.

Calculation modes
-----------------

Right after choosing the unit system, the text GUI asks for a calculation
mode: ``standard``, ``power-constrained``, or ``fixed-rpm``.

``standard``
    The unconstrained calculation used throughout the rest of this guide.
    Available power stays optional and only advisory: if the calculated
    power exceeds it, the result is shown anyway with a warning.

``power-constrained``
    Available power becomes a **required** field instead of an optional
    one. If your machine can already deliver the calculated power the
    result is unchanged. Otherwise the spindle speed is reduced until the
    power required matches what you supplied exactly, and the result label
    reads "adjusted to fit available power" instead of "recommended". A
    budget too small for any feasible spindle speed produces an error in
    the right pane — correct the available-power field in place to retry.

``fixed-rpm``
    Adds a required "Target spindle speed (RPM)" field. The spindle speed
    in the result is exactly what you entered — labeled "user-specified" —
    and every other value is recomputed for that speed. Available power
    stays optional/advisory here too, so an insufficient machine still
    produces a result, with a warning.

Switching mode on an open Milling screen clears any previous mode's
power/RPM answer rather than carrying it over as a stale default.

Reading the results
-------------------

A milling result looks like this::

    Spindle speed:     1989.4 RPM   (recommended)
    Feed rate:         397.9 mm/min
    Machining time:    0.25 min
    Torque:            0.6 N·m
    Power required:    0.13 kW
    Material removal:  3.98 cm³/min

The first five lines mean the same as they do for drilling. The extra line is
specific to milling:

**Material removal** (Q) is the volumetric material removal rate — how much
material the cut removes per minute. It is reported in cm³/min under metric
and in³/min under imperial. It is a useful sanity check on how aggressive a
cut is, and scales directly with depth of cut, engagement width and feed
rate. Drilling does not report a material removal rate, so that line never
appears in a drilling result.

If you supply an available machine power and the calculated power exceeds it,
the result is still shown, with a warning line telling you the cut is beyond
what the machine can deliver.

Limits and validation
---------------------

Milling inputs are validated as part of the calculation itself: an
out-of-range value produces a clear, actionable error in the right pane
rather than a result, and the field stays editable in place to correct it
— nothing is discarded and the session never aborts. Text that cannot be
parsed as a number at all is caught even earlier, before it ever reaches
the calculation, with its own distinct message. The bounds are configurable
(see the configuration documentation); the defaults are:

===============================  ==========  =========================================
Setting                          Default     Applies to
===============================  ==========  =========================================
``max_mill_diameter_mm``         200.0 mm    Cutter diameter.
``max_depth_of_cut_mm``          50.0 mm     Both axial depth *and* radial depth /
                                             width of cut.
``max_length_of_cut_mm``         1000.0 mm   Length of cut.
===============================  ==========  =========================================

In addition, every value must be a positive, finite number; the number of
teeth must be a whole number; and the radial depth / width of cut must not
exceed the cutter diameter.

Assumptions
-----------

The milling model assumes full, symmetric engagement and applies **no radial
chip-thinning compensation**. For light radial engagements the real chip load
is thinner than the nominal feed per tooth, so the calculated feed is
conservative. See ``specs/009-milling-calculations/research.md`` for the
formulas and their sources.
