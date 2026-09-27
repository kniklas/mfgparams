# Development setup

Detailed local build/test setup, environment toolset, and the troubleshooting
for the issues contributors actually hit. [`CONTRIBUTING.md`](CONTRIBUTING.md)
covers process (branching, spec-kit, review); the README covers using the
package once installed. This is the "make it build and test on my machine"
doc.

## Required toolset

| Tool | Version | Why |
|---|---|---|
| Git | any recent | clone/branch |
| Python | 3.9–3.12 | `pyproject.toml` sets `requires-python = ">=3.9"`; CI tests all four (Constitution Principle V). One is enough to start; all four if you want the full `tox` matrix locally. |
| pip | ≥ 21.2 (≥ 21.3 to match CI exactly) | see "pip too old" below |
| `tox` | pulled in by the `dev` extra | only needed for the multi-version matrix, not for a single-interpreter inner loop |
| [`pyenv`](https://github.com/pyenv/pyenv) (or `asdf`) | optional | manage several Python versions side by side if your OS doesn't ship 3.9–3.12 all at once |

## Setup steps

```bash
git clone https://github.com/kniklas/mfgparams.git
cd mfgparams

# Pick one interpreter explicitly — see "Wrong Python picked up" below for
# why a bare `python -m venv .venv` can bite you.
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Verify the install landed where you think it did:

```bash
python -c "import mfgparams, sys; print(mfgparams.__file__); print(sys.executable)"
```

Both paths should point inside `.venv/` in this checkout — not a system
Python, not a different clone, not a globally-installed `mfgparams`.

## Running tests

```bash
pytest                              # fast inner loop, whatever interpreter is active
tox                                 # full 3.9-3.12 matrix, serial
tox -p auto                         # same, in parallel
tox -e py39                         # one version only
tox -e py39 -- --no-cov -k drilling -x   # narrow down a failure (see tox.ini's comments on why --no-cov is required here)
tox -e packaging                    # wheel-contents assertions, run once (not per-version)
```

See the README's [Quality & Security Gates](README.md#quality--security-gates-ci)
table for what each CI job enforces, and the README's
["Checking every supported Python version locally"](README.md#checking-every-supported-python-version-locally)
section for the packaging-env/parallelism details.

## Releasing to PyPI

Publishing is automatic — there is no manual `twine upload` step. To cut a release:

1. Bump `__version__` in `src/mfgparams/__init__.py` (the single source of truth, per
   Constitution Principle IV).
2. Add a dated section to `CHANGELOG.md` for that version, moving the relevant entries out of
   `## [Unreleased]`.
3. Merge to `main` as usual.

Once `ci.yml` finishes successfully on `main`, `.github/workflows/publish.yml` fires
automatically (`workflow_run`), publishes the exact `dist/` artifact `ci.yml`'s own `build` job
already validated to PyPI via Trusted Publishing (OIDC — no stored API token), and the new
version is installable within minutes. A merge that doesn't change `__version__` is a safe
no-op; a failed publish can be retried from the Actions tab ("Re-run failed jobs") without a new
commit.

Before trusting a build-backend or packaging change with a real release, dry-run the pipeline
against TestPyPI first: from the Actions tab, run `publish.yml` via "Run workflow"
(`workflow_dispatch`) with `target: testpypi`, then install from
`https://test.pypi.org/simple/mfgparams` in a clean environment to confirm it works before the
next real merge publishes for real. See `specs/026-pypi-publish/quickstart.md` for the full
validation scenarios.

## Troubleshooting

### `pytest` fails with `ModuleNotFoundError: No module named 'mfgparams'`, or seems to run against old code

Your shell is picking up a `pytest`/`python` that isn't `.venv`'s — usually
because the venv was never activated in *this* shell, or a new terminal tab
was opened after activating in another one (activation is per-shell, not
per-checkout).

```bash
which pytest python        # both should resolve inside <repo>/.venv/bin/
```

If they don't: `source .venv/bin/activate` again, or bypass the question
entirely with `.venv/bin/pytest`. A `pipx`-installed global `pytest`, or a
different project's venv left active from an earlier `cd`, are the two most
common culprits.

### `pip install -e ".[dev]"` fails, hangs resolving, or silently produces a non-editable install

Almost always pip is too old. Python 3.9's bundled pip predates two things
this repo's install relies on:

- **pip ≥ 21.2** — needed to resolve `mfgparams[all]`, a self-referential
  extra (an extra that names the package's *other* extras rather than
  restating their dependencies).
- **pip ≥ 21.3** — needed for [PEP 660](https://peps.python.org/pep-0660/)
  editable installs (`-e`). Older pip either errors outright or falls back
  to a legacy `setup.py develop`-style install that doesn't behave
  identically — the symptom that bit the CI/tox setup here is
  `tests/unit/test_version_single_source.py` resolving a repo root that
  doesn't match how the package was actually installed.

```bash
python -m pip --version            # check what you're on
python -m pip install --upgrade pip
pip install -e ".[dev]"            # retry
```

Run the upgrade *before* the editable install, in the activated venv —
upgrading pip system-wide doesn't help if a stale one is what a
just-created venv bootstrapped from.

### `tox` reports some environments as `SKIPPED`

Expected when that Python version isn't installed on your machine —
`tox.ini` sets `skip_missing_interpreters = true` deliberately, so a
missing interpreter doesn't fail your run, it just narrows the matrix.
`SKIPPED` is not a failure; CI runs the full matrix regardless of what's
available locally.

To actually run all four locally, install the missing versions and make
sure they resolve as `pythonX.Y` on `PATH` — installing with `pyenv install`
alone is **not** enough, since `pyenv` only puts a version on `PATH` once
it's selected:

```bash
pyenv install 3.9.19 3.10.14 3.11.9 3.12.4   # whichever you're missing
pyenv global 3.9.19 3.10.14 3.11.9 3.12.4    # activates all four as shims
python3.9 --version                          # confirm each resolves before rerunning tox
tox
```

Prefer `pyenv global` over `pyenv local` here: `pyenv local` writes a
`.python-version` file into the repo root, which is **not** gitignored in
this project — an easy file to accidentally commit. If you do use `pyenv
local`, check `git status` before committing anything. Either way, list all
four versions together: passing just one deactivates the others for tox's
interpreter discovery.

### `tox -p` (parallel) corrupts a wheel or produces a flaky coverage failure

This was a real bug (issue #74), already fixed: the packaging-marked tests
(which shell out to `python -m build` into a shared `<repo>/build/`
directory) used to run inside the version matrix, so parallel envs raced on
that directory. They're now isolated to their own `tox -e packaging` target
outside `envlist`, which is what makes `tox -p auto` safe today. If you see
this on a clean checkout of current `main`, something's wrong — open an
issue rather than working around it.
