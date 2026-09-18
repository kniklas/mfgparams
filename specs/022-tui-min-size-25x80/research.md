# Research: TUI Minimum Terminal Size 25x80

## #1: Where do `MIN_COLUMNS`/`MIN_LINES` actually get consumed?

**Decision**: The only runtime consumer is `terminal_capability.check()`
(`src/mfgparams/console/tui/terminal_capability.py:57`), called once from
`cli.py::main()` before any prompt-toolkit object is constructed. The unsupported-terminal
message (`console.tui_unavailable`/`console.tui_unavailable.reason.too_small` in
`src/mfgparams/locales/en.py:54-62`) is parameterized with `{min_columns}`/`{min_lines}`,
not a literal `"30"`. So FR-001–FR-004 are satisfied by a single-line edit
(`MIN_LINES = 30` → `MIN_LINES = 25`) with **no** further code or catalog change needed —
the message automatically reflects the new floor in every supported locale.

**Rationale**: Confirmed by reading `cli.py` and `locales/en.py` directly (Principle XIII's
second bullet: verify against actual current source, not a paraphrase) rather than assuming
from the 018/017 features' own descriptions of this mechanism, which predate the message's
parameterization.

**Alternatives considered**: None — this is a factual lookup, not a design choice.

## #2: Which existing automated tests assert the old 80x30 boundary and need updating?

**Decision**: Exactly two files carry numeric boundary assertions tied to the old floor:

| File | What it asserts today | Update needed |
|---|---|---|
| `tests/unit/console/tui/test_terminal_capability.py` | `check()` returns `supported=True` at 80x30, `False` at 79x30 (columns boundary only — no existing case for the *old* lines boundary at exactly 80x29/80x30) | Add/adjust cases for the *new* 80x25 boundary: 80x25 → supported; 80x24 → unsupported. Keep the 80-column boundary cases (79x25 → unsupported) since `MIN_COLUMNS` is unchanged. |
| `tests/integration/test_tui_terminal_too_small.py` | 79x30 → rejected; 80x29 → rejected ("below the *new* 30-row floor but at-or-above the *old* 25-row one"); 80x30 → accepted; message contains `"30"` | Every one of these was written to specifically exercise the 018 boundary (25→30) and is now testing a value this feature retires. Rewrite using the same structure against 80x25: 79x25 → rejected; 80x24 → rejected; 80x25 → accepted; message contains `"25"`. |

**Rationale**: `grep`-confirmed via the actual test source (not carried over from the 018
feature's own docs) — both files' failure-mode comments explicitly reference the 25→30
change this feature reverses, so their old-boundary-specific assertions and comments no
longer describe reality once `MIN_LINES` is 25 again.

**Alternatives considered**: Leaving old-boundary assertions in place alongside new ones —
rejected; the old boundary (80x29/80x30) is no longer a meaningful edge for this
feature's floor and keeping dead assertions around would misdescribe the shipped behavior
to a future reader, the same class of drift Principle XIII's second bullet exists to catch.

## #3: Which of the six menu-reachable screens can actually clip at 80x25, vs. degrade gracefully?

**Decision**: The six screens split into two structurally different risk classes, confirmed
by reading `app.py`'s layout construction directly:

- **No scroll fallback — genuine clipping risk (FR-006's real target)**: the three
  operation screens (Drilling, Milling, Turning). Each renders as a fixed
  `Frame(body=operation_body, ...)` wrapped in a plain `Float` (`app.py:787,891-893`) with
  no scroll offset — if `operation_body`'s rendered height exceeds the terminal, prompt-toolkit
  simply cuts it off. This is exactly the case the 018-tui-splitpane-redesign's own
  `research.md #1` sized `MIN_LINES` around, and exactly the margin this feature removes.
- **Built-in scroll — not a clipping risk**: Configuration, About, Help (and the Machining
  tree dropdown). All four go through `_dropdown_float`'s `scrollable_dropdown_windows`
  mechanism (`app.py:789-797`), each with its own `vertical_scroll` int that prompt-toolkit
  clamps to the content's real extent and that the app already wires Up/Down key bindings
  to (`app.py:~1124-1147`). `app.py`'s own comment at line 789 explicitly names Configuration
  as a screen "that can outgrow the screen" *by design* — a user-supplied `--materials-config`
  can register arbitrarily many materials/tools, already taller than any fixed terminal floor
  could guarantee, and scrolling is the existing, intentional answer to that, not a gap this
  feature introduces.

**Consequence for FR-005/FR-006**: "fits without clipping" is interpreted as: content is
either fully visible, or fully reachable by scrolling with the existing bindings — not
necessarily fully visible simultaneously. Manual verification (Assumptions,
Principle XIII) MUST confirm Configuration/About/Help/the Machining tree remain scrollable
and reachable at 80x25 (FR-005's "usable" bar), but compaction (FR-006) is only realistically
on the table for Drilling/Milling/Turning, since those are the screens with no overflow
mechanism at all.

**Rationale**: Read directly from `app.py`'s layout-construction code and its own inline
comments (not inferred or assumed), per Principle XIII's requirement to verify claims about
reference/existing behavior against the actual current source.

**Alternatives considered**: Treating all six screens identically for FR-006 purposes —
rejected; it would either wrongly demand compaction work on screens that already handle
overflow correctly (wasted effort, and pressure to needlessly shrink Configuration's
data-driven, unbounded content), or wrongly excuse the three screens that actually can
clip.

**Correction (found during T008's manual verification, not caught by this analysis)**:
this finding's scope was *rows only* — it never checked whether a dropdown's *width* could
overflow the 80-column floor, only whether content could overflow vertically. Help, the
rightmost bar entry, does exactly that: at 80 columns its dropdown float (anchored via
`left=bar_offsets[...]`, 39) had only 41 columns before the screen edge, narrower than its
own configured width floor (40) once the `Frame`/`Shadow` border's overhead is subtracted —
it rendered squeezed to near-illegible, not a scrolling question at all. This was a real,
if latent, bug in `_dropdown_float`'s own claimed invariant ("never overflows even on an
80-column terminal," `app.py`'s prior docstring) that predates this feature but had
apparently never been exercised on a real 80-column terminal before this feature's manual
pass. Fixed by anchoring Help's float to the screen's right edge instead
(`right_aligned=True`), so its width is measured from the spacious left side of the screen
rather than the cramped 41 columns remaining to the right of its own trigger. About sits at
a similar risk (offset 32, only 5 columns of margin above its own width floor once border
overhead is subtracted) but was not observed to fail and was left unchanged, per
research.md #5's "smallest change that closes the gap" — revisit if manual verification
ever finds it actually squeezed too.

## #4: Which operation screen is likeliest to need compaction first?

**Decision**: Priority order for the manual-verification pass and any compaction that
follows, by static left-pane field count (a proxy for row count, not a substitute for the
Principle XIII manual check — actual rendered rows also depend on label/value text width
and terminal-specific wrapping):

| Operation | Left-pane fields (`FieldId` count in `rows_for`) | Prior row estimate |
|---|---|---|
| Milling | 14 (`unit_system, mode, sub_operation, material_type, material, tool, diameter, axial_depth_of_cut, radial_engagement, feed_per_tooth, number_of_teeth, length_of_cut, available_power, target_rpm`) | 16-17 rows per 018-tui-splitpane-redesign `research.md #1` (measured before this feature existed) |
| Turning | 11 (`unit_system, mode, material_type, material, tool, diameter, depth_of_cut, length_of_cut, available_power, target_rpm, target_feed_rate`) | Not previously measured — added after 018; PRs #100-#102 (combined-constraint modes, feed-per-rotation reporting) may have grown its row needs since initial addition |
| Drilling | 9 (`unit_system, mode, material_type, material, tool, diameter, depth, available_power, target_rpm`) | Smallest field count of the three; lowest a-priori risk |

**Rationale**: Every field renders as exactly one row (the 018 feature's Phase 9 reversal —
noted in its own `spec.md` — retired the `RadioList`-per-focused-field design in favor of a
permanent one-line `Label: value` summary for every field, so field count is a direct,
reliable proxy for row count here, unlike an earlier design where a focused field could
expand). Milling remains the most field-dense and the only one with a prior measurement;
Turning is untested territory this feature's manual-verification pass must cover for the
first time.

**Alternatives considered**: Skipping the row-count estimate and treating all three
operations as equal-priority unknowns — rejected; the field-count comparison is nearly free
(a `grep`) and materially informs where to spend manual-verification/compaction effort
first, without pretending to replace the actual on-terminal check.

## #5: Compaction technique, if manual verification finds a shortfall

**Decision**: No technique is prescribed in advance. If manual verification finds a screen
doesn't fit, the implementer picks the smallest change that closes the gap — tightening a
divider/border row, shortening a label, or reducing the bottom status row's max height —
scoped to `tasks.md` at that point, not designed speculatively here. `data-model.md`/
`contracts/` are not applicable to this decision (see Phase 1 below); this is deliberately
left open rather than over-specified, since the actual shortfall (if any) is unknown until
the manual pass runs.

**Rationale**: Speccing a compaction technique before knowing whether — or where — a
shortfall exists would be exactly the kind of anticipatory work Principle XIII's rationale
warns against: this project's history (018's own retrospective) shows guessing at a
rendering fix without looking at the real terminal has repeatedly produced wrong fixes.

**Alternatives considered**: Pre-selecting a specific compaction strategy (e.g., "always
drop the status row to 1 line first") — rejected as premature; the right fix depends on
which screen, if any, actually falls short and by how many rows.
