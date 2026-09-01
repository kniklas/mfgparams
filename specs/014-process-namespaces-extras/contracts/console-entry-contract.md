# Contract: Console Entry Point

**Feature**: [../spec.md](../spec.md) | **Requirements**: FR-007, FR-011, FR-012, Principle VIII

## Invocation forms

All three MUST work, with identical behaviour (FR-012):

| Form | Resolution |
|---|---|
| `mfgparams` | `[project.scripts]` → `mfgparams.__main__:main` |
| `python -m mfgparams` | `mfgparams/__main__.py` executed as `__main__` |
| `python -m mfgparams.console` | `mfgparams/console/__main__.py`, which delegates to `mfgparams.__main__:main` |

`mfgparams/__main__.py` therefore defines `main()` itself rather than re-exporting it, so the
console script and the module form resolve to the same function.

The third form exists because `mfgparams.console` is a package with a `cli` module in it, so
`python -m mfgparams.console` is a form a user reaches by guessing. **It MUST route through the
same guarded `main()`**, not call `console.cli.main` directly. FR-011 is unqualified — it is about
*invoking the console*, not about one entry point — so a bypass here would make one of the three
ways to start the console answer a missing dependency with a stack trace, with nothing to tell a
user which one they had picked. A maintainer who wants the raw import error has an explicit route
that does not need a second entry point: `python -c "from mfgparams.console.cli import main;
main()"`.

## Behaviour with console dependencies present

Identical to before this feature in every respect: same prompts, same order, same calculations, same
output text, same exit codes (FR-012). This slice moves the console; it does not touch its
behaviour.

## Behaviour with console dependencies absent (FR-011)

| Aspect | Requirement |
|---|---|
| Output | One short message naming the exact command that fixes it: `pip install mfgparams[console]` |
| Stream | stderr |
| Exit status | Non-zero |
| Traceback | MUST NOT be shown |
| Trigger | A dependency of the console failing to import — never a check for the console module, which always exists (see [installation-extras-contract.md](./installation-extras-contract.md)). The concrete construct is specified below. |

The guard MUST cover the lazy console import inside `main()` **and the console's own execution**,
and MUST NOT catch import failures originating from the core package — a genuinely broken core
install must still surface its own error rather than being misreported as a missing console.

Execution is covered because a console dependency need not be imported at the console's module
scope. #63 explicitly permits a heavy dependency to be imported lazily, inside the call; such an
import fails *after* `main()` has committed to running, so a guard wrapped around the import alone
emits exactly the raw traceback FR-011 forbids, on precisely the path the extra exists to describe.

## What the guard actually wraps

The `console` extra is empty on delivery, so there is no third-party import statement to wrap. The
guard is therefore written around the lazy console import and the call that follows it, separating
a missing *dependency* from a broken *core* by inspecting the exception:

```python
def main() -> int:
    try:
        from mfgparams.console.cli import main as _console_main
    except ModuleNotFoundError as exc:
        # A module inside our own distribution — or a *core runtime
        # requirement* a default install was supposed to bring in — failing to
        # import is a broken install, not a missing extra: let it surface as
        # itself, since `pip install mfgparams[console]` cannot fix it.
        if _is_broken_core(exc.name):
            raise
        return _report_missing_console(exc.name)

    try:
        status = _console_main()
    except ModuleNotFoundError as exc:
        # A different question, for a different reason (see below) — asked
        # *in addition to* the import-time one, which still applies.
        if _is_broken_core(exc.name) or not _requested_by_the_console(exc):
            raise
        return _report_missing_console(exc.name)

    if status is None:
        return 0
    if isinstance(status, int):
        return status
    print(status, file=sys.stderr)   # `sys.exit("message")` semantics
    return 1
```

Both guards run `_is_broken_core`, because the two questions are independent rather than
alternative. Provenance asks *did the console request this*; a module of **ours** that the console
lazily imported answers yes and is still a damaged install, so provenance alone would answer it
with `pip install mfgparams[console]` — advice that cannot work, and precisely what the "MUST NOT
catch import failures originating from the core package" rule above forbids.

This keeps the guard keyed on dependency availability while remaining implementable today: the
first `try` encloses the statement that will pull the first console dependency imported at module
scope, and the second covers one imported lazily during the run, so populating the extra requires
no change here.

### The two guards ask different questions, deliberately

They are not the same check applied twice. Each is the only one that works where it sits:

| | Import-time | Execution-time |
|---|---|---|
| Question | *what* is missing | *who asked for* what is missing |
| Predicate | `_is_broken_core(exc.name)` → re-raise | `_is_broken_core(exc.name)` → re-raise, **then** `_requested_by_the_console(exc)` → friendly |
| Default | friendly message | re-raise |

At import time the failure is by construction on the console's own import path, so the only thing
left to decide is whether the missing name is one of ours — an unrecognised third-party name is
most likely the missing extra, and gets the friendly message.

Once the console is *running*, that reasoning inverts: an arbitrary `ModuleNotFoundError` is a bug
somewhere inside it, and answering that with "install the console extra" would bury it. So the
default is to re-raise, and only a failure the console itself requested takes the friendly path.

**The execution-time predicate MUST NOT compare `exc.name` against the extra's declared
dependencies.** The gating extra records a **distribution** name (`PyYAML`) while the exception
carries an **import** name (`yaml`), and the two differ for a large class of packages —
`Pillow`/`PIL`, `beautifulsoup4`/`bs4`, `python-dateutil`/`dateutil`. Resolving one to the other
requires the distribution's own metadata, which is by definition *not installed* at the moment the
import fails. A name comparison therefore misses every such package, and since this guard's default
is to re-raise, every miss fails in the direction FR-011 forbids.

Provenance sidesteps the mapping entirely, and it is read in two steps:

1. **Find the innermost frame belonging to the console**, skipping the import machinery's own
   frames. No console frame means the console had no part in this, and it re-raises. *Innermost*,
   not first: a library the console called can call back into the console, and only the deeper
   frame describes what was actually attempted.
2. **Classify the frame directly below it.** Exactly three things appear there when the console's
   own statement asks the import system for a name: the **machinery**, a **module body**, or a
   module-level **`__getattr__`** (PEP 562, how a library spells a lazy submodule). Anything else
   is an ordinary call frame — the console called a function, and the failure belongs to that
   function.

The rule is narrow in both directions on purpose, and every neighbouring version of it is wrong:

| Rule | Shape it misreads |
|---|---|
| deepest non-machinery frame | `rich` installed with its own `pygments` missing: the deepest code frame is inside `rich`, so it blames `rich` and re-raises |
| ...and not a module body | a library resolving imports in a helper (`def _setup(): import pygments` at module scope, as `matplotlib` does) puts a *call* frame at the bottom of the console's own import |
| directly below, without the `__getattr__` marker | PEP 562: `from lib import thing` where `lib.__getattr__` does the import puts that call frame directly below, with the cascade beneath *it* |
| any import evidence *anywhere* below | over-corrects: a library the console **called** that runs its own `importlib.import_module` leaves a machinery frame down there, and its bug becomes "install the extra" |

The first three shapes are one failure — a **half-installed extra**, which `pip install
mfgparams[console]` repairs and FR-011 exists to describe. All three markers are load-bearing:
CPython elides the `importlib._bootstrap` frames from a plain failing `import`, so a module body is
often the only evidence an import ran, while `importlib.import_module` leaves machinery frames and
no module body.

**Skipping machinery in step 1 is not cosmetic.** `Path("<frozen importlib._bootstrap>").resolve()`
is interpreted relative to the working directory, so a process started *inside* the console
directory resolves a machinery frame to a path under it, and it would be taken for the innermost
console frame.

**One case is unresolvable and is decided deliberately.** A library whose import is simply wrong —
a typo, or an undeclared dependency imported unconditionally — produces a traceback identical in
shape to the half-installed one, both being "the console imported X; something under X was
missing". No rule reading frames can separate them. It is decided in favour of FR-011, which is a
requirement, over a clearer diagnostic for a library bug, which is not.

Every one of these decisions MUST be pinned by a test that fails when the decision is mutated: the
innermost-not-first scan, the machinery skip, and each of the three markers independently.

### A non-integer status is a message, not a number

`int(status)` MUST NOT be applied blindly. `return "some error"` / `sys.exit("some error")` is a
common convention, and coercing it raises `ValueError` *inside the entry point*, replacing whatever
the console was trying to say with the traceback this contract spends its length preventing. A
non-`int`, non-`None` status is therefore printed to stderr and reported as status `1`, matching
`sys.exit`.

### On `_core_requirement_roots` and the gating extra

`_is_broken_core` reads the core set out of installed metadata rather than restating it, so it
cannot drift from `pyproject.toml`. Note what that set is and is not: it holds the requirements
gated by **no** extra. It is *not* the complement of the console extra's requirements — anything
gated by `dev`, `test`, or a future runtime extra is in neither — so `_is_broken_core` returning
`False` means "not a core requirement", never "therefore a console dependency". That distinction is
why the execution-time guard needs its own question rather than the negation of this one.

`_is_broken_core` is what satisfies the "MUST NOT catch import failures originating from the core
package" rule above, and it is a rule with teeth — without it, a genuine `ImportError` inside
`console/cli.py` would be reported to the user as "install the console extra", sending them to fix
something that is not broken.

Only `ModuleNotFoundError` is caught, in both places. A bare `ImportError` (a module that exists but
fails while executing) is a real fault and MUST propagate.

The test for this path MUST simulate the failure at the dependency, not at the guard: patching the
guard's own condition would assert nothing about the behaviour FR-011 specifies.

This applies to the execution-time half too, and is easy to get wrong there — a stand-in `main()`
that raises `ModuleNotFoundError` directly, or a monkeypatched predicate, both leave the real
selection logic uncovered. The stand-in must run an actual `import` of a module that genuinely is
not installed, and control only *where* it appears to be imported from, since the console has no
lazy import site of its own yet. Mutating the predicate MUST break the suite; that is the check
that the test is testing anything.

## Message catalogue constraint (Principle VIII, and a constraint on slice 015)

The message is user-facing output, not logging, so Principle VIII applies: it MUST be a catalogue
entry with a stable message ID, not an inlined literal.

**The entry MUST live in the core catalogue and MUST remain there when slice 015 relocates message
catalogues into the console.**

The reason is structural, and it is the kind of thing that is obvious in hindsight and expensive to
discover late: this message exists to explain that the console is unavailable. If its catalogue
entry lives inside the console, the lookup fails exactly when the message is needed, and the user
receives the traceback FR-011 exists to prevent. Slice 015 inherits this as a contract, not as
advice.

## `mfgparams.console.__init__` MUST import nothing

`python -m mfgparams.console` reaches the guard *second*, not first: `runpy` imports the parent
package `mfgparams.console` before it executes `console/__main__.py`. Anything `console/__init__.py`
imports at module scope therefore fails **outside** `mfgparams.__main__:main`, and no guard can be
placed ahead of it — the interpreter gets there first. Verified by appending an import of an
absent module to that file: `python -m mfgparams` printed the friendly message and
`python -m mfgparams.console` printed a raw traceback.

So "all three forms behave identically" rests on this file importing nothing. That is not a
by-product of the file currently being docstring-only; it is a constraint, and
`tests/static/test_entry_points_are_guarded.py` fails if an import appears there. A convenience
re-export is the likely way it would be broken, and it would also pull the console's dependencies in
at package-import time — which is what the extra exists to avoid.

## Layering

`mfgparams/__main__.py` is the single exemption to the core-must-not-import-console rule
([package-layout-contract.md](./package-layout-contract.md)). Its import of the console MUST be
inside `main()`, never at module scope, so that importing the `mfgparams` package never imports the
console. This is asserted at runtime via `sys.modules`, not merely reviewed.
