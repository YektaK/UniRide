"""The line-ending rules of ``.gitattributes`` that make recorded sha256 values reproducible on every OS.

Several tests and run services compare the sha256 of a working-tree file with a value recorded earlier. Git stores such files
with LF; the recorded value is of the bytes a particular checkout holds, so the checkout must hold those bytes on every OS
(nightly CI 2026-10-23..27: a Linux checkout hashed the LF bytes while the values recorded on Windows are of CRLF bytes).

* study profiles and analysis plans are hashed by the run service and recorded as LF bytes: ``eol=lf``;
* the files of the 4sw5so archive root and the two WP-E10 re-run ``run_manifest.json`` files are recorded as the CRLF bytes of the
  Windows checkout that hashed them: ``eol=crlf``. Their ``figures/`` folder and every other archived file are not listed.

``git check-attr`` reads the rules; it needs no checkout of the files.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS = "docs/paper/results"

LF_FILES = [
    "academic_benchmark/studies/bildiri2026/study.json",
    "academic_benchmark/studies/bildiri2026/analysis_plan.json",
    "academic_benchmark/studies/yaem2026/study.json",
    "academic_benchmark/studies/yaem2026/analysis_plan.json",
]
CRLF_FILES = [
    f"{RESULTS}/week-2026-10-05-4sw5so/run_manifest.json",
    f"{RESULTS}/week-2026-10-05-4sw5so/2026-10-05_R50_repeat1.matrix.json",
    f"{RESULTS}/week-2026-10-05-4sw5so/2026-10-09_R90_repeat1.response.json",
    f"{RESULTS}/week-2026-10-05-4sw5so/README.md",
    f"{RESULTS}/week-2026-10-05-4sw5so/weekly.csv",
    f"{RESULTS}/week-2026-10-05-fleet-rerun-doblo-cap3/run_manifest.json",
    f"{RESULTS}/week-2026-10-05-fleet-rerun-large-sedan/run_manifest.json",
]
UNLISTED_FILES = [  # no conversion rule: byte-exact (-text) trees keep their own rule, the rest follows the checkout default
    f"{RESULTS}/week-2026-10-05-4sw5so/figures/index.html",
    f"{RESULTS}/week-2026-10-05-fleet-rerun-large-sedan/README.md",
    f"{RESULTS}/week-2026-10-05-fleet-rerun-doblo-cap3/README.md",
]


def _check_attr(attribute: str, path: str) -> str:
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not available to read .gitattributes")
    done = subprocess.run([git, "check-attr", attribute, "--", path], cwd=REPO_ROOT, capture_output=True, timeout=60)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    return done.stdout.decode("utf-8").strip().rsplit(": ", 1)[-1]


@pytest.mark.parametrize("path", LF_FILES)
def test_study_profiles_and_analysis_plans_are_checked_out_with_lf(path):
    assert _check_attr("eol", path) == "lf"
    assert _check_attr("text", path) == "set"


@pytest.mark.parametrize("path", CRLF_FILES)
def test_archived_files_with_recorded_crlf_hashes_are_checked_out_with_crlf(path):
    assert _check_attr("eol", path) == "crlf"
    assert _check_attr("text", path) == "set"


@pytest.mark.parametrize("path", UNLISTED_FILES)
def test_the_crlf_rule_is_scoped_to_the_hashed_files_only(path):
    assert _check_attr("eol", path) == "unspecified"


def test_the_listed_files_exist_in_the_repository():
    # a renamed or removed file would otherwise leave a rule (and these tests) pointing at nothing
    git = shutil.which("git")
    if git is None:
        pytest.skip("git is not available to list the tracked files")
    tracked = set(subprocess.run([git, "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, timeout=120)
                  .stdout.decode("utf-8").split("\0"))
    missing = [p for p in LF_FILES + CRLF_FILES + UNLISTED_FILES if p not in tracked]
    assert not missing, missing
