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
| Trigger | Failure to import the console's **dependencies** — never a check for the console module, which always exists (see [installation-extras-contract.md](./installation-extras-contract.md)) |

The guard MUST catch the import failure at the point of the lazy import inside `main()`, and MUST
NOT catch import failures originating from the core package — a genuinely broken core install must
still surface its own error rather than being misreported as a missing console.

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
