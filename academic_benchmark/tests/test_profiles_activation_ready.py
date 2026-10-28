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


def test_the_pinned_bildiri_profile_hash_holds_in_the_activated_state(activated):
    relative = "academic_benchmark/studies/bildiri2026/study.json"
    assert lf_sha256_of(activated, relative) == PINNED_LF_SHA256[relative]


def test_the_fixed_budget_golden_pin_of_the_profile_holds_in_the_activated_state(activated):
    relative = "academic_benchmark/studies/bildiri2026/study.json"
    assert relative in PINNED_FILES
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert _pinned_sha(relative, activated) == golden["pinned_files"][relative]
