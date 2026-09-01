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
        # A different question, for a different reason (see below).
        if not _requested_by_the_console(exc):
            raise
        return _report_missing_console(exc.name)

    return 0 if status is None else int(status)
```

This keeps the guard keyed on dependency availability while remaining implementable today: the
first `try` encloses the statement that will pull the first console dependency imported at module
scope, and the second covers one imported lazily during the run, so populating the extra requires
no change here.

### The two guards ask different questions, deliberately

They are not the same check applied twice. Each is the only one that works where it sits:

| | Import-time | Execution-time |
|---|---|---|
| Question | *what* is missing | *who asked for* what is missing |
| Predicate | `_is_broken_core(exc.name)` → re-raise | `_requested_by_the_console(exc)` → friendly |
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

Provenance — the deepest traceback frame that belongs to someone's code rather than to the import
machinery — sidesteps the mapping entirely. Whatever it is called, a module the console itself
imported is the console's dependency. A failure raised from inside a third-party library the console
merely *called* is that library's bug, and still re-raises.

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

## Layering

`mfgparams/__main__.py` is the single exemption to the core-must-not-import-console rule
([package-layout-contract.md](./package-layout-contract.md)). Its import of the console MUST be
inside `main()`, never at module scope, so that importing the `mfgparams` package never imports the
console. This is asserted at runtime via `sys.modules`, not merely reviewed.
