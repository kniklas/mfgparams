Milling calculations (user guide)
=================================

mfgparams calculates parameters for two milling sub-operations —
**end milling** and **face milling** — alongside drilling. This page covers
using them from the interactive CLI; see :doc:`milling-api` for the library
API.

Selecting an operation in the REPL
----------------------------------

Start the REPL with::

    python -m mfgparams

The first question is which machining operation to calculate. Choosing
``milling`` adds a second question for the sub-operation::

    Machining operation (drilling, milling) (drilling): milling
    Milling operation (end milling, face milling) (end milling): end milling
    Unit system [metric/imperial] (metric):
    Calculation mode (standard, power-constrained, fixed-rpm):
    Material type (Metal, Wood): Metal
    Material (Mild Steel, Stainless Steel, ...): Mild Steel
    End-mill tool (HSS, Cobalt, Carbide, Coated Carbide): Carbide

Both prompts accept the option text (not a number), and both offer a default
in parentheses that you can accept by pressing Enter. Choosing ``drilling``
leads to exactly the drilling session that existed before milling was added.

After each result the REPL asks whether to run another calculation. Answering
yes returns to the operation prompt, so you can switch operations freely.
Each operation remembers its *own* previous answers as defaults, so hopping
from end milling to drilling and back does not lose your milling inputs.

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

Right after choosing the unit system, the REPL asks for a calculation mode::

    Calculation mode (standard, power-constrained, fixed-rpm):

``standard``
    The unconstrained calculation used throughout the rest of this guide.
    Available power stays optional and only advisory: if the calculated
    power exceeds it, the result is shown anyway with a warning. Unlike the
    unit-system prompt above, the mode prompt has no editable default — you
    must type one of the three options; a blank entry re-prompts instead of
    silently accepting ``standard``.

``power-constrained``
    Available power becomes a **required** prompt instead of an optional
    one. If your machine can already deliver the calculated power the
    result is unchanged. Otherwise the spindle speed is reduced until the
    power required matches what you supplied exactly, and the result label
    reads "adjusted to fit available power" instead of "recommended". A
    budget too small for any feasible spindle speed is rejected with a
    re-prompt.

``fixed-rpm``
    Adds a required "Target spindle speed (RPM)" prompt. The spindle speed
    in the result is exactly what you entered — labeled "user-specified" —
    and every other value is recomputed for that speed. Available power
    stays optional/advisory here too, so an insufficient machine still
    produces a result, with a warning.

Answering ``y`` at the "run another calculation?" prompt returns to the
operation prompt, where you can pick a different mode; any previous
mode's power/RPM answer is cleared rather than carried over as a stale
default.

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

Milling inputs are validated before anything is calculated, and an invalid
value is re-prompted rather than aborting the session. The bounds are
configurable (see the configuration documentation); the defaults are:

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
