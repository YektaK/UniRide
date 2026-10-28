"""The paper campaign starts from an approval commit that changes only ``"status": "draft"`` -> ``"status": "active"`` in the
four real files (``studies/{bildiri2026,yaem2026}/{study,analysis_plan}.json``).

These tests build that activated state in a temporary directory on every normal run (the real files are never touched) and
apply the pin checks the real tests use, so an activation-breaking pin is caught before the approval commit, not at it.
The activation edit is written out here by hand, independently of ``profile_status``, so a defect in the helper cannot hide
itself.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from academic_benchmark.tests.profile_status import assert_real_status, draft_normalised_bytes, draft_normalised_sha256
from academic_benchmark.tests.test_exact_reference_boundaries import PINNED_LF_SHA256, lf_sha256_of
from academic_benchmark.tests.test_fixed_budget_tables_unchanged import GOLDEN, PINNED_FILES, _pinned_sha

REPO = Path(__file__).resolve().parents[2]
STUDIES = ("bildiri2026", "yaem2026")
FOUR_FILES = tuple(f"academic_benchmark/studies/{study}/{name}" for study in STUDIES for name in ("study.json", "analysis_plan.json"))
DRAFT = b'"status": "draft"'
ACTIVE = b'"status": "active"'


def _activate_copy(target_root: Path) -> None:
    """The approval commit's edit on copies of the real files: the one status line, nothing else.

    A real file that is already active (after the approval commit) is copied as it is."""
    for relative in FOUR_FILES:
        data = (REPO / relative).read_bytes()
        assert data.count(DRAFT) + data.count(ACTIVE) == 1, f"{relative} has no single draft/active status line"
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data.replace(DRAFT, ACTIVE, 1))


@pytest.fixture()
def activated(tmp_path):
    _activate_copy(tmp_path)
    return tmp_path


def test_the_activation_edit_changes_exactly_one_line_per_file(activated):
    for relative in FOUR_FILES:
        real = (REPO / relative).read_bytes()
        edited = (activated / relative).read_bytes()
        assert edited.count(ACTIVE) == 1 and edited.count(DRAFT) == 0
        assert edited.replace(ACTIVE, DRAFT, 1) == real.replace(ACTIVE, DRAFT, 1)  # every other byte is the real file's
        assert json.loads(edited)["status"] == "active"


def test_the_normalisation_helper_is_loud_on_any_unexpected_shape():
    ok_draft, ok_active = b'{\n  "status": "draft",\n  "x": 1\n}', b'{\n  "status": "active",\n  "x": 1\n}'
    assert draft_normalised_bytes(ok_draft) == ok_draft
    assert draft_normalised_bytes(ok_active) == ok_draft
    assert draft_normalised_sha256(ok_active) == draft_normalised_sha256(ok_draft)
    for bad in (
        b'{"x": 1}',  # no status line
        b'{"status": "retired"}',  # another status
        b'{"status": "draft", "n": {"status": "active"}}',  # both forms
        b'{"status": "active", "n": {"status": "active"}}',  # a repeated line
        b'{"status": "draft", "n": {"status": "draft"}}',
        b'{"status":"active"}',  # the exact string only: other spacing is not understood
    ):
        with pytest.raises(AssertionError):
            draft_normalised_bytes(bad)


def _statuses(root: Path) -> dict:
    return {relative: json.loads((root / relative).read_text(encoding="utf-8"))["status"] for relative in FOUR_FILES}


def _assert_one_status_for_all(root: Path) -> None:
    statuses = _statuses(root)
    assert set(statuses.values()) <= {"draft", "active"}, statuses
    assert len(set(statuses.values())) == 1, f"half-done approval: the four files must carry one status, got {statuses}"


def test_the_four_real_files_carry_the_same_status():
    # lead decision A18 (b): one approval commit activates both studies, profiles and plans together
    _assert_one_status_for_all(REPO)


def test_a_half_done_approval_is_caught(tmp_path, activated):
    _assert_one_status_for_all(activated)  # all four active: fine
    half = tmp_path / "half"
    for relative in FOUR_FILES:
        target = half / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((activated / relative).read_bytes())
    one = half / FOUR_FILES[0]
    one.write_bytes(one.read_bytes().replace(ACTIVE, DRAFT, 1))  # only one of the four files left draft
    with pytest.raises(AssertionError, match="half-done"):
        _assert_one_status_for_all(half)


def test_a_changed_non_status_byte_changes_the_normalised_hash(activated):
    relative = "academic_benchmark/studies/bildiri2026/study.json"
    data = (activated / relative).read_bytes()
    tampered = data.replace(b'"study_id": "bildiri2026"', b'"study_id": "bildiri2027"', 1)
    assert tampered != data
    assert draft_normalised_sha256(tampered) != draft_normalised_sha256(data)


def test_the_real_files_carry_exactly_draft_or_active():
    for relative in FOUR_FILES:
        assert_real_status(json.loads((REPO / relative).read_text(encoding="utf-8"))["status"])
    with pytest.raises(AssertionError):
        assert_real_status("retired")


def test_the_pinned_bildiri_profile_hash_holds_in_the_activated_state(activated):
    relative = "academic_benchmark/studies/bildiri2026/study.json"
    assert lf_sha256_of(activated, relative) == PINNED_LF_SHA256[relative]


def test_the_fixed_budget_golden_pin_of_the_profile_holds_in_the_activated_state(activated):
    relative = "academic_benchmark/studies/bildiri2026/study.json"
    assert relative in PINNED_FILES
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert _pinned_sha(relative, activated) == golden["pinned_files"][relative]
