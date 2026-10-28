"""Test helper: the committed study profiles and analysis plans may be ``draft`` or ``active``.

The paper campaign starts from an approval commit that changes only the ``"status": "draft"`` line of the four real files
(``studies/<id>/study.json`` and ``studies/<id>/analysis_plan.json``, both studies) to ``"status": "active"``. The tests that pin
those files must therefore hold in both states without losing any other pinned byte, and the tests that exercise
draft behaviour (inference refused, paper mode refused) must build their draft input explicitly instead of relying on the
committed status. Never point paper mode at the real repository root: once the profile is active it would start the real campaign.

* ``draft_normalised_bytes`` / ``draft_normalised_sha256``: the file bytes with the status line normalised back to the draft
  form, so a sha256 pin recorded in the draft state keeps pinning every other byte in both states.
* ``assert_real_status``: the committed status is exactly ``draft`` or ``active``, nothing else.
* ``copy_real_study_as``: copy a real study's profile, plan and dataset manifests into a temporary repository in a chosen state.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Optional

DRAFT_LINE = b'"status": "draft"'
ACTIVE_LINE = b'"status": "active"'
REAL_STATUSES = ("draft", "active")


def draft_normalised_bytes(data: bytes) -> bytes:
    """``data`` with ``"status": "active"`` replaced (exactly once) by ``"status": "draft"``.

    The file must hold exactly one status line of exactly one of the two forms; anything else (no status line, both forms, a
    repeated line) raises ``AssertionError`` so a pin never passes on a file this helper did not understand.
    """
    drafts, actives = data.count(DRAFT_LINE), data.count(ACTIVE_LINE)
    if (drafts, actives) == (1, 0):
        return data
    if (drafts, actives) == (0, 1):
        return data.replace(ACTIVE_LINE, DRAFT_LINE, 1)
    raise AssertionError(
        f"expected exactly one of {DRAFT_LINE!r} / {ACTIVE_LINE!r}, found {drafts} draft and {actives} active status lines"
    )


def draft_normalised_sha256(data: bytes) -> str:
    return hashlib.sha256(draft_normalised_bytes(data)).hexdigest()


def assert_real_status(status: str) -> None:
    """The status of a committed real profile or plan: exactly ``draft`` or ``active``."""
    assert status in REAL_STATUSES, f"committed status must be one of {REAL_STATUSES}, got {status!r}"


def copy_real_study_as(
    repository_root: Path, study: str, target_root: Path, study_status: str, plan_status: Optional[str] = None
) -> str:
    """Copy ``studies/<study>/study.json``, ``analysis_plan.json`` and the dataset manifests into ``target_root``.

    The profile gets ``study_status`` and the plan ``plan_status`` (default: the profile's); each is ``"draft"`` or
    ``"active"``. Apart from that one line every byte is the real file's, whatever state the real file is in. Returns the
    repository-relative study path.
    """
    plan_status = study_status if plan_status is None else plan_status
    source_dir = repository_root / "academic_benchmark" / "studies" / study
    target_dir = target_root / "academic_benchmark" / "studies" / study
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, status in (("study.json", study_status), ("analysis_plan.json", plan_status)):
        assert status in REAL_STATUSES, status
        data = draft_normalised_bytes((source_dir / name).read_bytes())
        if status == "active":
            data = data.replace(DRAFT_LINE, ACTIVE_LINE, 1)
        (target_dir / name).write_bytes(data)
    profile = json.loads((target_dir / "study.json").read_text(encoding="utf-8"))
    for ref in profile["dataset_manifest_refs"]:
        target = target_root / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(repository_root / ref, target)
    return f"academic_benchmark/studies/{study}/study.json"
