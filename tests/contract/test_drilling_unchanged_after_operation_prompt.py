"""Contract test: drilling is byte-for-byte unchanged by the refactor (T014).

FR-002 / SC-005 require that introducing the operation-selection prompt does
not alter drilling at all. ``run()`` was split into per-operation session
functions to make room for milling, so the only way to prove drilling's
behaviour survived intact is to compare a live session against a transcript
captured from the pre-refactor CLI.

``tests/contract/data/drilling_baseline_session.txt`` is that transcript, and
``drilling_baseline_input.txt`` is the scripted input that produced it (task
T013a). A diff here means drilling actually changed — regenerate the fixture
only when the change is intended and reviewed.
"""

import builtins
from pathlib import Path

import pytest

from mfgparams.console.cli import run
from mfgparams.console.i18n import translate

_DATA = Path(__file__).parent / "data"
_BASELINE = _DATA / "drilling_baseline_session.txt"
_BASELINE_INPUT = _DATA / "drilling_baseline_input.txt"

#: The one prompt the refactor legitimately adds, ahead of everything else.
_OPERATION_PROMPT = translate(
    "en",
    "cli.prompt.choice",
    label="Machining operation",
    options="drilling, milling",
    suffix=" (drilling)",
)


@pytest.fixture
def baseline_answers():
    return _BASELINE_INPUT.read_text().splitlines()


def _run_with(monkeypatch, capsys, answers):
    """Replay ``answers``, echoing each prompt so stdout matches a real TTY."""

    supply = iter(answers)

    def _input(prompt=""):
        print(prompt, end="")
        return next(supply)

    monkeypatch.setattr(builtins, "input", _input)
    run()
    return capsys.readouterr().out


def test_drilling_session_matches_the_pre_refactor_baseline(monkeypatch, capsys, baseline_answers):
    out = _run_with(monkeypatch, capsys, ["drilling", *baseline_answers])

    assert out.startswith(_OPERATION_PROMPT), "the operation prompt must come first"
    remainder = out[len(_OPERATION_PROMPT) :]

    assert remainder == _BASELINE.read_text()


def test_baseline_fixture_is_present_and_non_trivial():
    """Guard against the comparison silently passing on an empty fixture."""

    baseline = _BASELINE.read_text()

    assert "Spindle speed:" in baseline
    assert "Feed rate:" in baseline
    assert "Power required:" in baseline
    # Drilling never reports a material removal rate (research.md #7).
    assert "Material removal:" not in baseline


def test_selecting_drilling_by_pressing_enter_gives_the_same_session(
    monkeypatch, capsys, baseline_answers
):
    """Drilling is the offered default, so a bare Enter must reach it too."""

    out = _run_with(monkeypatch, capsys, ["", *baseline_answers])

    assert out[len(_OPERATION_PROMPT) :] == _BASELINE.read_text()
