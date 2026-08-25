"""Tests pinning the shared machining-operation enums (T055).

``MachiningOperation`` and ``MillingSubOperation`` are public API (exported
in ``mfgparams.__all__``) and their string values are load-bearing:
``data-model.md`` pins the exact values, the CLI REPL prompts dispatch on
them, and (per FR-013/imperial round-trip contracts) they are stable
identifiers a caller could persist. Before this test existed (found in the
``speckit.converge`` audit, F3) nothing under ``tests/`` referenced either
enum directly, so a silent rename of a member or its value would break API
consumers with an otherwise-green test suite.
"""

from mfgparams.models import MachiningOperation, MillingSubOperation


def test_machining_operation_values_are_pinned():
    assert MachiningOperation.DRILLING.value == "drilling"
    assert MachiningOperation.MILLING.value == "milling"


def test_machining_operation_has_no_extra_members():
    assert [member.name for member in MachiningOperation] == ["DRILLING", "MILLING"]


def test_milling_sub_operation_values_are_pinned():
    assert MillingSubOperation.END_MILLING.value == "end-milling"
    assert MillingSubOperation.FACE_MILLING.value == "face-milling"


def test_milling_sub_operation_has_no_extra_members():
    assert [member.name for member in MillingSubOperation] == [
        "END_MILLING",
        "FACE_MILLING",
    ]
