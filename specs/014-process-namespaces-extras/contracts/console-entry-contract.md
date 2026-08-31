# Contract: Console Entry Point

**Feature**: [../spec.md](../spec.md) | **Requirements**: FR-007, FR-011, FR-012, Principle VIII

## Invocation forms

Both MUST work, with identical behaviour (FR-012):

| Form | Resolution |
|---|---|
| `mfgparams` | `[project.scripts]` → `mfgparams.__main__:main` |
| `python -m mfgparams` | `mfgparams/__main__.py` executed as `__main__` |

`mfgparams/__main__.py` therefore defines `main()` itself rather than re-exporting it, so the
console script and the module form resolve to the same function.

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

The guard MUST catch the import failure at the point of the lazy import inside `main()`, and MUST
NOT catch import failures originating from the core package — a genuinely broken core install must
still surface its own error rather than being misreported as a missing console.

## What the guard actually wraps

The `console` extra is empty on delivery, so there is no third-party import statement to wrap. The
guard is therefore written around the lazy console import itself, and separates a missing
*dependency* from a broken *core* by inspecting the exception:

```python
def main() -> int:
    try:
        from mfgparams.console.cli import main as _console_main
    except ModuleNotFoundError as exc:
        # A module inside our own distribution failing to import is a broken
        # install, not a missing extra — let it surface as itself.
        if exc.name is not None and exc.name.split(".")[0] == "mfgparams":
            raise
        print(get_message("console.missing_dependency"), file=sys.stderr)
        return 1
    return _console_main()
```

This keeps the guard keyed on dependency availability while remaining implementable today: the
`try` encloses the statement that will pull the first console dependency the moment one is added to
`mfgparams/console/cli.py`, so populating the extra requires no change here. The `exc.name` check
is what satisfies the "MUST NOT catch import failures originating from the core package" rule
above, and it is a rule with teeth — without it, a genuine `ImportError` inside `console/cli.py`
would be reported to the user as "install the console extra", sending them to fix something that
is not broken.

Only `ModuleNotFoundError` is caught. A bare `ImportError` (a module that exists but fails while
executing) is a real fault and MUST propagate.

The test for this path MUST simulate the failure at the dependency, not at the guard: patching the
guard's own condition would assert nothing about the behaviour FR-011 specifies.

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
