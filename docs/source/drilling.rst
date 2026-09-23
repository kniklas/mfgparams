Drilling calculations (user guide)
===================================

mfgparams calculates parameters for twist-drill **drilling**, alongside
milling (end milling and face milling). This page covers using it from the
interactive text GUI; see :doc:`drilling-api` for the library API.

Selecting an operation in the text GUI
---------------------------------------

Launch the text GUI with::

    mfgparams

(equivalently, ``python -m mfgparams`` or ``python -m mfgparams.console`` —
all three reach the same interface.) A persistent menu bar stays visible at
the top of the screen: **Exit**, **Machining**, **Configuration**, **About**,
**Help** — each reachable with the arrow keys and Enter, or its underlined
keyboard shortcut. Selecting **Machining** expands a tree in place, showing
**Milling** and **Drilling** as flat leaves; selecting **Drilling** opens
its operation screen directly, with no further tree-level expansion. It
appears as a centered, bordered floating window over the menu bar and tree
(which stay visible underneath, untouched): the left pane lists every
drilling input at once (unit system, calculation mode, material type,
material, drilling tool, drill diameter, hole depth, available power), all
simultaneously visible and editable, with no separate screen per field; the
right pane shows the live result, updating automatically as you fill in or
change an input. Choosing **Milling** instead switches to the flow described
in :doc:`milling`.

**Up/Down** (or **j/k**) always moves to the next/previous field, regardless
of its type. A radio field (unit system, mode, material type, material, and
tool) is always a single ``Label: value`` line — **Left/Right**/**h/l**/
**Space** cycle its value with wraparound and commit it immediately, with no
separate confirm step. Once **metal** is chosen as the material type, the
Material field also opens a dedicated selection window on **Enter**, on top
of that ordinary cycling — see `Selecting a metal material`_ below. Numeric
fields (drill diameter, hole depth, available
power) become editable the instant you select them — start typing a digit
(or ``.``/``-``) and it edits the field's buffer immediately, no separate
"start editing" step; Left/Right nudges the buffer up or down by a small
step; Backspace removes the last character. That text is only written to
the field once you navigate away from it (Up/Down) — text that still
doesn't parse as a number at that point is discarded (the field keeps its
last valid value) and a message appears in the status bar beneath both
panes until you correct it.

Pressing Escape moves focus back to the menu bar without closing the open
operation window or changing the tree's expand/collapse state — so you can
collapse the Machining tree to see more of the screen without losing your
place. Pressing Escape again, from the menu bar, closes the operation and
returns to the menu bar/tree, letting you start another calculation — the
same operation or a different one — without leaving the text GUI. Each
operation remembers its *own* previous answers as defaults for the rest of
the session, so switching from drilling to milling and back does not lose
your drilling inputs.

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
selected (if any) highlighted, and every search field cleared. A materials
config file can add ``material_number``/``short_notation`` to a
``[[materials]]`` entry to make it searchable this way too — see
``specs/023-material-selector-dialog/contracts/materials-config-schema-delta.md``.
Non-metal material types are unaffected and only ever offer the ordinary
Left/Right/Space radio-cycling behavior, with no selection window.

Drilling inputs
----------------

After the unit system, calculation mode, material type, material and tool,
drilling asks for two geometry values:

===========================  =========================================================
Prompt                       Meaning
===========================  =========================================================
Drill diameter                Diameter of the twist drill, in mm / in.
Hole depth                    Depth of the hole to be drilled, in mm / in.
===========================  =========================================================

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
    one, and the result label always reads "adjusted to fit available
    power" instead of "recommended" — regardless of whether an adjustment
    actually happened. If your machine can already deliver the calculated
    power the numeric values are unchanged even though the label switches.
    Otherwise the spindle speed is reduced until the power required
    matches what you supplied exactly. A budget too small for any feasible
    spindle speed produces an "infeasible power budget" error in the right
    pane in place of a result — correct the available-power field in place
    to retry, without leaving the screen.

``fixed-rpm``
    Adds a required "Target spindle speed (RPM)" field. The spindle speed
    in the result is exactly what you entered — labeled "user-specified" —
    and every other value is recomputed for that speed. Available power
    stays optional/advisory here too, so an insufficient machine still
    produces a result, with a warning.

Switching mode on an open Drilling screen clears any previous mode's
power/RPM answer rather than carrying it over as a stale default.

Reading the results
--------------------

A drilling result looks like this (10 mm diameter, 25 mm depth, Mild Steel,
Carbide, standard mode)::

    Spindle speed:     1989.4 RPM   (recommended)
    Feed rate:         437.7 mm/min
    Machining time:    0.06 min
    Torque:            10.5 N·m
    Power required:    2.18 kW

These five lines mean the same as they do for milling: spindle speed and
feed rate describe how the drill is driven, machining time is how long the
hole takes to cut, and torque/power are what the spindle needs to deliver.
Drilling does not report a material removal rate — that line is specific to
milling and never appears in a drilling result.

If you supply an available machine power and the calculated power exceeds
it, the result is still shown, with a warning line telling you the cut is
beyond what the machine can deliver.

Limits and validation
----------------------

Drill diameter and hole depth are validated as part of the calculation
itself: an out-of-range value produces a clear, actionable error in the
right pane rather than a result, and the field stays editable in place to
correct it — nothing is discarded and the session never aborts. Text that
cannot be parsed as a number at all (rather than a number that is merely
out of range) is caught even earlier, before it ever reaches the
calculation, with its own distinct message. The bounds themselves are:

===============================  ==========  =========================================
Setting                          Default     Applies to
===============================  ==========  =========================================
``max_diameter_mm``              100.0 mm    Drill diameter.
``max_depth_mm``                 500.0 mm    Hole depth.
===============================  ==========  =========================================

In addition, both values must be positive, finite, and within the bound
above. ``NaN``, ``+inf``/``-inf`` and non-numeric values are all rejected
as ``INVALID_DIAMETER``/``INVALID_DEPTH`` before the bound is checked, so
the CLI re-prompts for them — including the literal ``nan`` that
``float()`` happily parses as ``nan`` — rather than
letting a ``NaN`` poison the calculation (fixed in issue #56).

Library callers
can override these bounds via ``calculate()``'s ``config_path`` argument
(see :doc:`drilling-api`); the CLI does not expose an equivalent flag — its
only configuration flag, ``--materials-config``, overrides materials/tools,
not these geometry bounds.

Assumptions
-----------

The drilling model uses standard twist-drill machining formulas as
published in widely-referenced industry sources (Sandvik Coromant's
"Machining Formulas" reference and Machinery's Handbook), including a
point-engagement allowance approximated as a fraction of drill diameter to
account for the drill point's cutting geometry when computing machining
time. See ``specs/001-metal-drilling-calc/research.md`` for the formulas
and their sources.
