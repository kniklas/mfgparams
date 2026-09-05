# Contract: which catalogue owns which key

**Feature**: [../spec.md](../spec.md) | **Requirements**: FR-001, FR-002, FR-004, SC-001

## The rule

A message key lives in exactly one catalogue — **except the two exceptions the table below
documents explicitly** — determined by this table, not by convention:

| Key pattern | Owner | Why |
|---|---|---|
| `cli.*` | `mfgparams.console.locales.*` | Console-rendered prompt/label/status text (FR-001). |
| `material_type.*` | `mfgparams.console.locales.*` | Console-rendered category label — a UI string, not material data (distinct from `WorkpieceMaterial.translations`; see Story 3). |
| `error.*`, `warning.*`, `notice.*` — **English text** | `mfgparams.locales.*` | Core-owned per FR-005: must render (in English) with no import of anything console-owned, for a library caller without the `console` extra. Includes `error.materials_config.*`/`notice.materials_config.*` (`RegistryConfigError`/`MergeResult`), which already carry this same reasoning today. |
| `error.*` — **non-English translations**, once any exist | `mfgparams.console.locales.*` | Not this feature's scope to add (spec Assumptions), but FR-005a and `data-model.md` are explicit: a future French `error.invalid_diameter.max` entry is new console-catalogue content keyed by the same `message_key`, not a copy of core's English row above. `_render_error` in `console/cli.py` only ever looks there for it. The row above governs the English original; this row governs any translation of it. |
| `console.missing_dependency*` | `mfgparams.locales.*` | Inherited constraint from [014's console-entry contract](../../014-process-namespaces-extras/contracts/console-entry-contract.md) — a message announcing the console is unavailable cannot live where it can't be looked up (FR-002). This is a `console.*`-prefixed key that stays in core, precisely because of what it says. |
| `cli.label.axial_depth_of_cut`, `cli.label.radial_depth_of_cut`, `cli.label.width_of_cut` | **Both** | Found during implementation (T007), not assumed up front — spec.md's Assumptions section is corrected accordingly. `validate_depth_of_cut_mm`/`validate_engagement_mm` embed one of these, resolved via `translate()`, as `{label}` inside their core-owned English `message` (FR-005). Core needs its own English copy to do that without the console installed; console keeps its copy for the matching prompt label. Genuinely dual-use, not an oversight — but exactly the kind of thing FR-004's "no key in both catalogues" default should have flagged as a risk in `/speckit-clarify` rather than being discovered in code. |

Outside the two documented exceptions above, no key legitimately exists in both catalogues. A key
relocated by this feature MUST be removed from its previous location in the same change (FR-004) —
no alias, no dual lookup, for any key other than these two exceptions.

## Enforcement

Convention alone regresses silently (this is exactly what 014's `console-entry-contract.md` warns
about for its own guard). This feature is enforced by:

- `tests/static/test_console_catalogue_ownership.py` (new, five checks). A first version scanned
  only literal second arguments to `translate()`/`has_message()` calls — a Copilot review found this
  missed real keys reached via a module-level lookup dict (`_MODE_OPTION_KEYS` and similar) and via a
  chain of same-file function parameters (`label_key`/`engagement_label_key`, sometimes several
  wrapper functions deep). The current version traces both: a small fixed-point analysis marks a
  parameter "key-consuming" if it is used directly as a `translate()`/`has_message()` key or passed
  into another already-key-consuming parameter, then collects every literal ever bound to one,
  anywhere in the file. The same review found the identical gap on the core side —
  `_reject_if_invalid`'s `error_message_key` keyword-only parameter fed `ErrorInfo(message_key=...)`
  without ever appearing as a literal at that call site — so the same fixed-point machinery is reused
  for `message_key=` too, not hand-special-cased. The five checks:
  1. Every console key found this way (direct, dict-literal, or parameter-chain) exists in
     `mfgparams.console.locales.en.MESSAGES`, except `console.missing_dependency*`.
  2. `translate`/`has_message` in `console/cli.py` are bound **only** from `mfgparams.console.i18n` —
     checked directly, since check 1 assumes a bare `translate`/`has_message` call means the
     console's catalogue, and reverting the import to `mfgparams.i18n` would otherwise leave check 1
     green while console keys silently render as raw IDs.
  3. `console.missing_dependency*` is present in core's catalogue and absent from the console's.
  4. Every `message_key` found the same way (direct or `error_message_key`-chained) across
     **every non-console Python source file** (not a hardcoded list of the three modules known
     at the time this feature was implemented — the scan walks `src/mfgparams` excluding the
     `console` subtree, so a new process module added later is covered automatically) exists in
     `mfgparams.locales.en.MESSAGES` — confirms research.md #4's move did not over-relocate
     something core still needs.
  5. The two catalogues' key sets are disjoint, except `console.missing_dependency*` and the three
     `cli.label.*` depth/engagement keys (present in **both**, by design — see the table above).
- The existing `tests/static/test_no_hardcoded_strings.py` (Principle VIII) continues to apply
  unchanged — a literal string still cannot be inlined at any call site, in either package; this
  feature only changes *which* catalogue the non-literal lookup targets.
- The two `RegistryConfigError`/`materials_load_notice` call sites in `console/cli.py` render through
  core's `translate` (aliased `_translate_core` there), not the console's — they pass a *dynamic* key
  (`exc.message_key`/`notice_key`), so no static scan sees them either way; they are correct by
  construction (a different imported name), not by a check that inspects them individually.

## Non-goals

- This contract does not require a non-English catalogue to exist on either side (spec Assumptions
  — this feature relocates infrastructure, it does not add translations).
- This contract does not change `i18n.get_locale`/`get_raw_locale`'s resolution rules
  (`MFGPARAMS_LOCALE`, no OS auto-detection) on either side — both loaders keep that behavior
  identically (research.md #1).
