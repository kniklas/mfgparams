# Feature Specification: Multi-Notation Metal Material Selector Dialog

**Feature Branch**: `[023-material-selector-dialog]`

**Created**: 2026-09-22

**Status**: Draft

**Input**: User description: "after selecting metal (all operations) a new floating window is opened to select metal using simple name (as currently) or using material number notaion (1.xxxx+N) or shortened notatation (e.g. 42CrMo4+N); ideally 3 name types (simple, material number, shortened notation) are displayed next to each other, with ability to make partial search in each column, navigating up and down arrow between different names, enter to select and close metal material selection window, escape to close window and cancel"

## Clarifications

### Session 2026-09-22

- Q: When the common-name column displays and searches a material's name, should it use the material's translated display name for the active UI locale, or always the canonical English name? → A: Use the translated display name for the active display locale (falling back to English per the existing i18n rule); search matches against that same translated text.
- Q: When the material selection window opens and the field already had a previously selected material, should the candidate list start with that material highlighted, or always start at the top of the full list? → A: Highlight the previously selected material (if still present in the unfiltered list) when the window opens.

### Session 2026-09-23 (post-implementation amendment)

- Direct user feedback, after the feature was first implemented and Left/Right/Space cycling was disabled for the metal Material row (Enter-only): it must remain possible to select a metal material with Left/Right/Space one at a time, exactly as before this feature, *in addition to* Enter opening the detailed selection window — not one replacing the other. FR-001 and the Assumptions below are updated to match; FR-013 gains a bullet requiring a hint naming Enter's extra behavior on this row where the UI has room for one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find a metal material by its common name in a dedicated picker (Priority: P1)

A user setting up a drilling, turning, or milling calculation reaches the material step and, once the "metal" category is chosen, opens a dedicated selection window instead of scrolling an inline list. They type part of the material's common name and the list narrows to matching materials; they move the highlighted row up or down, press Enter to select it and close the window, or press Escape to close the window and keep whatever material was previously selected.

**Why this priority**: This is the foundation of the feature — a searchable, keyboard-driven picker for the identification method users already rely on today. Without it, the other two identification methods have nothing to attach to.

**Independent Test**: Can be fully tested by opening the material selector for a metal material with only common-name search active, typing a partial name, confirming the candidate list narrows correctly, and confirming Enter/Escape behave as described — delivers a working, searchable replacement for today's material selection on its own.

**Acceptance Scenarios**:

1. **Given** the material selection window is open with no search text entered, **When** the user types a partial common name, **Then** only metal materials whose common name contains that text (case-insensitive) remain in the list.
2. **Given** a filtered list of candidate materials, **When** the user presses the Down or Up arrow key, **Then** the highlighted row moves to the next or previous candidate in the list.
3. **Given** a material is highlighted, **When** the user presses Enter, **Then** that material becomes the selected material for the current calculation and the selection window closes.
4. **Given** the selection window is open (with or without search text entered), **When** the user presses Escape, **Then** the window closes and the material that was selected before the window was opened remains unchanged.
5. **Given** a material was already selected before the window was opened, **When** the window opens, **Then** that material's row is highlighted in the full, unfiltered candidate list without the user pressing any arrow key first.

---

### User Story 2 - Find a metal material by its EN material number (Priority: P2)

A user who knows a metal's standardized material number (e.g. `1.7225`) but not its common name opens the same selection window and types the number, or part of it, into the material-number column. The candidate list narrows to materials whose material number contains that text, independent of what (if anything) is typed into the common-name column.

**Why this priority**: Engineers and machinists frequently reference metals by their EN material number rather than a marketing/common name; without this, users who only know the number must guess or look it up elsewhere before they can search at all.

**Independent Test**: Can be fully tested by opening the picker, typing a partial material number into the material-number column, and confirming the candidate list narrows to materials whose material number matches — delivers standalone value even if the shortened-notation column (User Story 3) is not yet available.

**Acceptance Scenarios**:

1. **Given** the material selection window is open, **When** the user types a partial material number into the material-number column, **Then** only metal materials whose material number contains that text remain in the list, and the same row highlighting/Enter/Escape behavior from User Story 1 applies.
2. **Given** a metal material has no material number recorded, **When** the user types any non-empty text into the material-number column, **Then** that material is excluded from the filtered list (its material-number cell displays as blank when not filtered out).

---

### User Story 3 - Find a metal material by its shortened designation (Priority: P3)

A user who knows a metal's shortened designation (e.g. `42CrMo4+N`) opens the same selection window and types it, or part of it, into the shortened-notation column, narrowing the candidate list the same way the other two columns do.

**Why this priority**: Completes the three identification methods called for by the feature; lower priority than User Story 2 because the shortened designation is generally less universally used for lookups than the EN material number, but still valuable for users trained on DIN-style short names.

**Independent Test**: Can be fully tested by opening the picker, typing a partial shortened designation into the shortened-notation column, and confirming the candidate list narrows accordingly — delivers standalone value on top of User Stories 1 and 2.

**Acceptance Scenarios**:

1. **Given** the material selection window is open, **When** the user types a partial shortened designation into the shortened-notation column, **Then** only metal materials whose shortened designation contains that text remain in the list.
2. **Given** all three columns (common name, material number, shortened designation) have search text entered simultaneously, **When** the candidate list is filtered, **Then** only materials matching all three search texts at once remain in the list.

---

### Edge Cases

- What happens when the combined filters across the three columns match no material? The list shows an empty/no-matches state, the highlight has nothing to select, and Enter has no effect until the user adjusts a filter or presses Escape.
- What happens when a metal material has no recorded material number and/or no recorded shortened designation? Its cell(s) in the corresponding column display as blank, and that material is excluded whenever the user types a non-empty search in that column (an empty value cannot match non-empty search text), but it remains selectable via any column the user leaves empty.
- What happens if the user selects a material, reopens the window, and searches again? The window opens with all three search columns empty and the full metal material list shown, discarding any prior search text — but the row for the previously selected material starts highlighted (per FR-011), so the user sees their current choice before typing anything new.
- What happens when the metal material list is long enough to exceed the visible window height? The list scrolls, and arrow-key navigation moves the highlight into view as needed.
- What happens if the user presses Enter while the filtered list is empty? Nothing is selected and the window remains open.
- What happens on a non-metal material category (e.g. wood)? This feature applies to metal material selection only; other categories keep their existing selection behavior (see Assumptions).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST, once the "metal" material category is chosen during drilling, turning, or milling setup, let the user open a dedicated material selection window on Enter, in addition to (not instead of) still being able to cycle the material one at a time with Left/Right/Space the same way every other radio field works (Session 2026-09-23 amendment).
- **FR-002**: The material selection window MUST display, for every candidate metal material, three values side by side: the common name (shown in the active display locale's translated form, falling back to English when no translation exists, consistent with how material names are already displayed elsewhere in the console), the EN material number notation, and the shortened designation.
- **FR-003**: The material selection window MUST provide an independent, editable search field for each of the three columns; the common-name search field MUST match against the same locale-specific translated text FR-002 displays for that column, not the underlying canonical English name.
- **FR-004**: System MUST filter the candidate list to materials whose value in a given column contains the search text entered in that column (case-insensitive, partial/substring match), and MUST combine non-empty filters across all three columns so that only materials matching every non-empty filter remain.
- **FR-005**: System MUST let the user move a single highlighted selection up and down through the current candidate list using the Up and Down arrow keys.
- **FR-006**: System MUST let the user switch which column's search field currently receives typed characters, without losing the search text already entered in the other columns.
- **FR-007**: System MUST, when the user presses Enter while a candidate is highlighted, set that material as the selected material for the current calculation and close the selection window.
- **FR-008**: System MUST, when the user presses Enter while the candidate list is empty, take no action and leave the selection window open.
- **FR-009**: System MUST, when the user presses Escape at any point while the selection window is open, close the window without changing the material that was selected before the window was opened.
- **FR-010**: System MUST leave a metal material's material-number and/or shortened-designation cell blank in the selection window when that value is not recorded for the material, and MUST exclude such a material whenever the user enters non-empty search text in the corresponding column.
- **FR-011**: System MUST reset the candidate list (to the full metal material list) and all three search fields (to empty) each time the selection window is opened. If a material was already selected before the window opened and is present in that full list, System MUST set the initial row highlight to that material; otherwise the window MUST open with no row highlighted.
- **FR-012**: System MUST apply this selection window consistently across drilling, turning, and milling setup wherever a metal material is chosen.
- **FR-013**: All labels and messages the selection window displays (column headers, empty-state text, etc.) MUST be sourced from the project's translatable message catalog rather than hard-coded text, consistent with the project's existing internationalization approach.
- **FR-014**: While the metal Material field is selected but its selection window is not open, System SHOULD show a brief hint that Enter opens the detailed selection window, wherever the surrounding UI already has a place for such a hint (Session 2026-09-23 amendment); this is a SHOULD, not a MUST, since a terminal/layout too narrow to show it MUST NOT be treated as a defect.

### Key Entities

- **Metal Material**: A selectable workpiece material belonging to the "metal" category. Gains two new identifying attributes alongside its existing common name: an EN material number notation (e.g. `1.7225+N`) and a shortened designation (e.g. `42CrMo4+N`). Either or both new attributes MAY be absent for a given material. The common name displayed and searched in the selection window is the material's translated display name for the active display locale (English fallback applies per the project's existing i18n rule).
- **Material Selection Window**: A transient, focusable overlay presented over the current operation's setup screen. Holds the current candidate list (derived from the full metal material list filtered by the three search texts), the current row highlight, and which of the three search fields currently has input focus. Discarded without side effects on cancel; on confirm, yields exactly one selected metal material back to the setup screen it was opened from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who knows a metal material's common name, its EN material number, or its shortened designation can locate and select that material using only that one identifier, without needing to know either of the other two.
- **SC-002**: Every metal material that has a recorded EN material number or shortened designation is findable by typing that value (or a distinctive partial value) into the corresponding column.
- **SC-003**: Users can back out of the selection window at any time and, 100% of the time, find the previously selected material unchanged.
- **SC-004**: The selection window behaves identically (same columns, search, navigation, and confirm/cancel keys) whether reached from drilling, turning, or milling setup.
- **SC-005**: Narrowing a multi-hundred-entry metal material list to a handful of candidates via search takes a user under 10 seconds of typing and reading, without needing to scroll through the unfiltered list first.

## Assumptions

- This feature applies only to selecting materials in the "metal" category, matching the feature description's repeated use of "metal"; selection of non-metal categories (e.g. wood) is out of scope and keeps its current inline behavior.
- The EN material number notation and shortened designation are new data attributes that must be added to the material reference data; they are populated for metal materials where a standard designation is known and left blank otherwise, per FR-010's edge-case handling. Populating this data for every existing metal material is a data-entry task tracked separately from this feature's interaction behavior.
- All three columns always reflect the same underlying candidate list (one row per material, three cells per row) rather than three independently-scrolling lists; the Up/Down highlight is shared across all three columns.
- Switching which column receives typed search input (FR-006) uses a standard secondary key (e.g. Tab/Shift+Tab or Left/Right arrow) distinct from Up/Down, which are reserved for moving the row highlight; the exact key is a presentation detail left to implementation/design review, not fixed by this specification.
- Partial search matching is substring-based and case-insensitive in all three columns, consistent with how search/filtering already behaves elsewhere in the console UI.
- The material selection window is a keyboard-only interaction (no mouse/pointer requirement), consistent with the rest of the console TUI.
