# Contract: `ErrorInfo`'s locale behaviour after this feature

**Feature**: [../spec.md](../spec.md) | **Requirements**: FR-005, FR-005a, FR-005b, FR-006, FR-007

## The contract

1. `ErrorInfo.message` is **always English**, regardless of `MFGPARAMS_LOCALE` or an explicit
   `locale=` argument passed to a library call. Before this feature, `message` varied with locale;
   after it, `message` is a pure function of *which validation failed*, not of *which locale was
   active*. This is a breaking change to `CalculationResult.error`'s observable behaviour and is
   accumulated toward the same 2.0.0 bump as [014](../../014-process-namespaces-extras/spec.md)
   (spec Assumptions).

2. `ErrorInfo.code` is unchanged in meaning and value for every existing error. No existing test
   asserting `result.error.code == "..."` needs to change.

3. `ErrorInfo.message_key` and `ErrorInfo.kwargs` are new. `message_key` is populated for every
   `ErrorInfo` the core constructs — there is no code path that returns an `ErrorInfo` without one.
   `kwargs` defaults to `()` and is populated whenever the corresponding catalogue entry has
   placeholders.

4. A library caller with the `console` extra **not installed** gets a fully usable result from
   `CalculationResult.error` using only `code` and `message` — nothing about `message_key`/`kwargs`
   requires the console to be present; they are plain data on a dataclass defined in core.

5. The console, when installed and rendering in a non-English active locale, MUST render error text
   by calling `translate(locale, error.message_key, **dict(error.kwargs))` against **its own**
   catalogue (`mfgparams.console.i18n.translate`, not `mfgparams.i18n.translate`) — never by
   attempting to translate the English `error.message` string itself, and never by branching on
   `error.code`.

6. The console, when rendering in the **English** active locale, MUST display `error.message`
   directly. It MUST NOT call its own `translate()` for error text in this case — there is nothing
   to look up that isn't already sitting in `error.message`, and doing so anyway would require an
   English copy of every error key in the console's catalogue, which research.md #3 rules out.

## What this contract does NOT require

- It does not require every `message_key` to have a translated entry in every console-bundled
  locale. Per the existing `i18n.translate` fallback rule (Principle VIII, unchanged by this
  feature), a missing key or locale falls back to English — in the console's own catalogue, using
  the console's own English text if one exists there, or (if the console's English catalogue has no
  entry for that `message_key` at all, which is the expected case since this feature ships no
  non-English catalogue) the console falls back to `error.message` rather than raising or
  displaying a raw key. Item 4 of research.md's consequence note applies: the *mechanism* is what
  ships, not translated text.
- It does not require `ErrorInfo` to remain byte-for-byte serializable in whatever form it was
  before (e.g., if any caller does `dataclasses.astuple(error)` or similar) — this is a shape
  change, and the spec's Assumptions place it inside the same major-version bump as 014's other
  breaking changes.

## Verification

- `tests/contract/test_library_api_milling_locale.py` (rewritten, FR-007): asserts `message` is
  English regardless of `locale=`/`MFGPARAMS_LOCALE`, and asserts `message_key`/`kwargs` are
  populated and correct for at least one error per exercised code path.
- A new unit test (`tests/unit/test_error_info_rerendering.py`, SC-006) exercises the
  `INVALID_DIAMETER` zero/max pair specifically: two `ErrorInfo` values sharing `code` MUST have
  different `message_key`s, and re-rendering each through a fixture non-English catalogue (mirroring
  the existing `_FIXTURE_LOCALE` pattern) MUST produce two different translated strings.
- `tests/unit/test_config_milling_bounds.py` and the `processes/machining/**/test_calculate.py`
  suites, which assert on `result.error.code`, are the regression evidence that `code` is untouched.
