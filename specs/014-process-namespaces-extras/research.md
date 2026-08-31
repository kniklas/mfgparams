# Phase 0 Research: Process Namespaces and Installation Extras

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-08-30

Both of the spec's clarifications were resolved before planning, so no `NEEDS CLARIFICATION`
markers entered this phase. The items below are the design unknowns the plan surfaced.

---

## 1. Enforcing that the core never imports the console (FR-008)

**Decision**: A static test that parses every module under `src/mfgparams/` **except**
`mfgparams/__main__.py` with `ast`, and fails if any `import`/`from` statement names
`mfgparams.console`. Paired with a runtime assertion that importing `mfgparams` (and each
`processes.*` module) leaves `mfgparams.console` absent from `sys.modules`.

**Rationale**: The two checks fail on different mistakes and neither subsumes the other. The AST
check catches an import that is never executed at import time (inside a function, or behind
`TYPE_CHECKING`) and states the rule declaratively where a reader will find it. The `sys.modules`
check catches an import laundered through an intermediary — core importing a module that imports
the console — which the per-file AST scan cannot see. Together they make FR-008 enforced rather
than documented, which is what the requirement demands.

`mfgparams/__main__.py` is exempt because `python -m mfgparams` requires a `__main__.py` at the
package root and the interpreter accepts no other location (FR-012). The exemption is narrowed by
requiring its console import to be *inside* the function body, so importing the `mfgparams` package
still never pulls the console — that laziness is what the `sys.modules` assertion actually verifies.

**Alternatives considered**:

- *`import-linter` with a contract file*: purpose-built and expressive, but adds a dev dependency
  and a second configuration language for one rule that is ~30 lines of test code. Rejected for
  proportionality; worth revisiting if the layering rules multiply.
- *Convention plus code review*: rejected outright — FR-008 says "MUST be enforced automatically,
  not by convention", and this is precisely the kind of rule that decays silently.
- *Runtime check only*: cheaper, but blind to a `TYPE_CHECKING`-guarded or function-local import
  that would still couple the layers on paper and mislead the next reader.

---

## 2. What an installation extra actually gates

**Decision**: Ship one distribution containing every module, including `mfgparams.console`. The
`console` extra adds *dependencies*, not modules. The FR-011 guard therefore keys on whether the
console's **dependencies** import successfully, never on whether the console module exists.

**Rationale**: This is the single most consequential correction the research turned up. An extra is
purely a dependency group — `pip install mfgparams` installs the whole wheel, so
`mfgparams.console` is importable whether or not the user asked for `[console]`. A guard written as
"is `mfgparams.console` importable?" would therefore *never* fire, and the missing-dependency path
of FR-011 would be dead code that tests could only reach by monkeypatching the check itself. Keying
on the dependency import makes the guard fire under exactly the real-world condition it exists for.

Today the console's dependency set is empty, so the guard cannot fire in practice. That is expected
and is why the spec's Assumptions declare the extra now: the guard and its test encode the
contract before there is a dependency to trip it, so that adding the first console dependency is a
one-line change rather than a rediscovery of this whole design.

**Alternatives considered**:

- *Two distributions (`mfgparams` and `mfgparams-console`)*: gives a genuine module-level split, so
  the guard could key on module presence. Rejected as disproportionate — two release processes, two
  version numbers to keep in lockstep, and a cross-distribution version-compatibility problem, all
  to avoid one `try/except ImportError`. Revisit only if the console grows heavy dependencies that
  a majority of library users would resent.
- *Guarding on a recorded install-time marker* (e.g. a sentinel file written by the extra):
  rejected because extras write no such marker, and any hand-rolled equivalent would drift from
  reality — precisely the "partially-installed console" edge case the spec calls out.

---

## 3. Verifying relocated bundled data ships in the wheel (FR-015)

**Decision**: Extend the existing `packaging`-marked assertions
(`tests/integration/test_packaging_bundled_data.py`) to the new data paths, and additionally assert
that **no** `data/*.toml` file exists under the old paths in the built artifact.

**Rationale**: `[tool.setuptools.package-data]` lists three explicit `operations/**/data/*.toml`
globs — a fourth entry, `data/*.toml`, is core `materials.toml` and is unaffected. Every one of the
three is invalidated by this move, and the failure mode is silent in the worst possible
way: the library imports fine from a source checkout, passes the whole suite there, and fails only
at first use of an installed wheel. The repository already learned this lesson once — those
assertions were `importorskip`-ed in every environment until spec 013 made `build` a real test
dependency — so the mechanism exists and only its paths need updating. The negative assertion is
new: without it, a stale glob left behind in `package-data` would keep passing while shipping files
nobody references.

These tests carry the `packaging` marker, so they run in CI's `build` job and `tox -e packaging`,
not in the version matrix (spec 013 / issue #75 P1.3). No marker or gate composition changes here.

**Alternatives considered**:

- *A recursive `mfgparams = ["**/data/*.toml"]` glob*: removes the per-path maintenance entirely.
  Tempting, and worth considering on its own merits — but it changes packaging behaviour beyond
  this feature's "mechanical move" remit (it would also capture data directories added later
  without review), so it belongs in its own change rather than buried in a restructure.

---

## 4. The missing-console message and Principle VIII (forward-compatibility trap)

**Decision**: The FR-011 message gets a stable message ID with its English text in the **core**
catalog (`mfgparams/locales/en.py`), and it MUST stay in core when slice 015 relocates the other
catalogs to the console.

**Rationale**: Principle VIII requires user-facing strings to come from a catalog rather than being
inlined, so the guard's message needs an entry. The trap is in the interaction with slice 015: that
slice moves message catalogs into `mfgparams.console`. A message whose entire purpose is to explain
that *the console is unavailable* cannot be looked up from a catalog that lives inside the console —
the lookup would fail exactly when the message is needed, and the user would get the traceback
FR-011 exists to prevent.

Recording this now costs one sentence; discovering it during slice 015 would mean either shipping
that bug or reopening this slice's design. This constraint is written into
[contracts/console-entry-contract.md](./contracts/console-entry-contract.md) so slice 015 inherits
it as a contract rather than as a comment in a research file.

**Alternatives considered**:

- *Inline the English string in the guard*: simplest, and defensible since the message is arguably
  diagnostic rather than user-facing. Rejected because it is unambiguously printed to the user on
  stderr, and Principle VIII's carve-out is for *logging*, not for user-visible output.
- *Defer the decision to slice 015*: rejected — the whole point of finding it now is that slice 015
  would find it too late.

---

## 5. Preventing reintroduction of the old layout (FR-017)

**Decision**: A new static test modelled directly on `tests/static/test_no_old_package_name.py`:
walk every git-tracked file's content *and its tracked path*, and fail on `mfgparams.operations`,
`mfgparams/operations`, or a re-created `src/mfgparams/operations/` path — with the same three
exclusion categories that test already established (prior specs as historical record, the
constitution, and the check's own source).

**Rationale**: Reusing the existing pattern rather than inventing one keeps two near-identical
checks legible side by side, and that test already solved the subtle part: scanning tracked *paths*
as well as contents is what catches a re-added compatibility shim, whose contents would contain no
forbidden string to scan for. That is exactly the FR-004 violation most likely to be reintroduced
by a well-meaning future contributor.

This slice's own `specs/014-*/` documents necessarily name the old paths to describe the migration,
so they join the historical-record exclusion — with the same care that test takes: excluding the
directory, not the string, so live files stay covered.

**Alternatives considered**:

- *Extending `test_no_old_package_name.py` in place*: rejected. Its exclusion list is tuned to a
  different question (the old distribution name) and its docstring is a careful historical record;
  overloading it with a second rule would make both harder to reason about.

---

## 6. Sequencing the move so it stays reviewable

**Decision**: Perform the relocation with `git mv` per directory, in a commit that contains *only*
moves and the mechanical import rewrites they force. New behaviour (the FR-008 guard, the FR-011
path, the FR-015 and FR-017 tests, packaging metadata, docs) lands in separate commits on top.

**Rationale**: The precedent is direct: the package rename (#68) touched 143 files in one PR and
reviewed cleanly because the mechanical part was mechanical throughout. Rename detection only holds
when a moved file's contents are nearly unchanged, so mixing a behavioural edit into the move
commit turns a reviewable `R100` into an add/delete pair that hides the real change. Keeping the
split also means a reviewer can verify FR-003 (no behaviour change) by confirming the move commit
contains no content edits beyond import lines.

**Alternatives considered**:

- *One commit for everything*: rejected — it makes FR-003 unverifiable by inspection, which is the
  cheapest evidence available for a no-behaviour-change requirement.
- *A PR per directory moved*: rejected — the intermediate states would not import, so no
  intermediate PR could pass CI, which is the condition that would have forced Principle XII.

---

## 7. Configuration surfaces that reference module paths

**Decision**: Audit and update, in the same PR: `[tool.setuptools.package-data]` (three moving globs),
`[project.scripts]`, the Sphinx pages `docs/source/drilling-api.rst` and `docs/source/milling-api.rst`,
and the README's structure/installation sections.

**Rationale**: These are the surfaces that name module paths as *data* rather than as imports, so
no test failure and no import error points at them; only an explicit audit does. `--cov=mfgparams`,
`[tool.coverage.run] source`, `[tool.mypy] files`, and the ruff/black configs all address the
package root and are unaffected by internal reorganisation — verified by reading each setting, not
assumed.

**Alternatives considered**: none; this is an inventory, not a choice. It is recorded here so
`/speckit-tasks` produces a task per surface rather than one vague "update config" task.
