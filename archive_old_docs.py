#!/usr/bin/env python3
"""
archive_old_docs.py — Move outdated documentation to archive/docs/

USAGE
  python archive_old_docs.py            # DRY_RUN (preview, no moves)
  python archive_old_docs.py --force    # Actually move files
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

DRY_RUN = "--force" not in sys.argv
PROJECT_ROOT = Path(__file__).resolve().parent
ARCHIVE_ROOT = PROJECT_ROOT / "archive" / "docs"

# --- Files verified as resolved/outdated via codegraph ---
RESOLVED_AND_OUTDATED = [
    "docs/05_Code_Quality_Roadmap.md",
    "docs/BENCHMARK_ARCHITECTURE_DEBT.md",
    "docs/01_Implementation_Status.md",
    "docs/06_COMPREHENSIVE_REVIEW_AND_RECOMMENDATIONS.md",
    "docs/09_04_2026_Codebase_Analysis_Report.md",
    "docs/00_13.04.2026_QWEN_CODE_REVIEW_REPORT.md",
    "docs/REFACTORING_REPORT_APRIL_13_2026.md",
    "docs/ACADEMIC_BENCHMARK_FIX_REVIEW_2026-05-09.md",
    "docs/00_05.05.2026_academic_audit_report.md",
    "docs/01_05.05.2026_SOTA_compliance_fix_log.md",
    "docs/05.05.2026_academic_fix_plan.md",
    "docs/05.05.2026_consolidation_plan.md",
    "docs/00_08.05.2026.GPT5.4-pro.Academic Benchmark Remediation Master Dossier.md",
    "docs/08.05.2026.GPT5.4-pro.Academic Benchmark Engineering Action Plan.md",
    "docs/08.05.2026.GPT5.4-pro.Academic Benchmark Patch Checklist.md",
    "docs/08.05.2026.GPT5.4-pro.Compact_implementation_tickets.md",
    "docs/08.05.2026.GPT5.4-pro.Commit_Execution_Plan.md",
    "docs/08.05.2026.GPT5.4pro.Academic_Benchmark_Analysis.md",
    "docs/08.05.2026_code_review_report.md",
    "docs/08.05.2026_code_review_report.UPDATED.GPT5.4.pro.md",
    "docs/01_Independent_Code_Review_v4_Verification.md",
    "docs/gwo-hho-strategy-review.md",
    "docs/sota_benchmark_analysis.md",
    "docs/BENCHMARK_STUDIO_INTEGRATION_REPORT.md",
    "docs/BENCHMARK_INTEGRATION_CHECKLIST.md",
    "docs/BENCHMARK_CVRPTW_STRATEGY.md",
    "docs/ARCHITECTURE_INTEGRATION_GUIDE.md",
    "docs/ARCHITECTURE_QUICK_REFERENCE.md",
    "docs/02_Architecture.md",
    "docs/03_Roadmap.md",
    "docs/ARCHIVING_LOG.md",
    "docs/UNIVERSAL_PROBLEM_SELECTOR_IMPLEMENTATION_PLAN.md",
    "docs/UNIVERSAL_PROBLEM_SELECTOR_PLAN.v0.md",
    "docs/UNIVERSAL_PROBLEM_SELECTOR_PLAN.v1.md",
    "docs/UNIVERSAL_PROBLEM_SELECTOR_PLAN.v2.md",
]

ROOT_LEVEL_OUTDATED = [
    "00_code_review_reportOpus4.6.31.05.2026.md",
    "00_UniRide_Unified_Master_Plan_2026_05_26_00.40_opus4.6.md",
    "00walkthrough.v2.md",
    "implementation_plan_fcm_hybrid.md",
    ".ai-handover.md",
]

ROOT_DUPLICATES = [
    "01.06.2026_UniRide_Archive_Classification_Report.md",
    "01.06.2026_UniRide_Comprehensive_Code_Review.md",
]

DOCS_DEV = [
    "docs_dev/task_plan.md",
    "docs_dev/progress.md",
    "docs_dev/findings.md",
    "docs_dev/academic_benchmark_fix_report.md",
]

ARCHIVE_DIRECTORIES = [
    "archive",
    "docs/old",
    "docs/archive",
    "docs/superpowers",
    "academic_benchmark/bildiri2026/archive_old",
    "academic_benchmark/bildiri2026/archive_old_20260425_0245",
    "optimizer_api/strategies/_archived",
]


def move_file(src, dst, dry_run):
    if not src.exists():
        return False
    if dry_run:
        print(f"  [DRY] {src.relative_to(PROJECT_ROOT)} -> {dst.relative_to(PROJECT_ROOT)}")
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    print(f"  [OK]  {src.relative_to(PROJECT_ROOT)} -> {dst.relative_to(PROJECT_ROOT)}")
    return True


def move_directory(src, dst, dry_run):
    if not src.exists() or not src.is_dir():
        return 0
    count = 0
    for filepath in sorted(src.rglob("*")):
        if filepath.is_file():
            rel = filepath.relative_to(src)
            if move_file(filepath, dst / rel, dry_run):
                count += 1
    return count


def main():
    print("=" * 70)
    if DRY_RUN:
        print("  DRY RUN — no files will be moved. Pass --force to execute.")
    else:
        print("  LIVE RUN — files WILL be moved to _project_archive/docs/")
    print("=" * 70)
    print()

    manifest_lines = [f"# Archive Manifest — {datetime.now().isoformat()}", ""]
    total = 0

    all_files = RESOLVED_AND_OUTDATED + ROOT_LEVEL_OUTDATED + ROOT_DUPLICATES + DOCS_DEV
    print(f"-- Individual files ({len(all_files)} candidates) --")
    for relpath in all_files:
        src = PROJECT_ROOT / relpath
        dst = ARCHIVE_ROOT / relpath
        if move_file(src, dst, DRY_RUN):
            manifest_lines.append(f"FILE  {relpath}")
            total += 1
    print()

    print(f"-- Directories ({len(ARCHIVE_DIRECTORIES)} candidates) --")
    for relpath in ARCHIVE_DIRECTORIES:
        src = PROJECT_ROOT / relpath
        dst = ARCHIVE_ROOT / relpath
        count = move_directory(src, dst, DRY_RUN)
        if count > 0:
            manifest_lines.append(f"DIR   {relpath} ({count} files)")
            total += count
    print()

    if not DRY_RUN:
        manifest_lines.append("")
        manifest_lines.append(f"Total files moved: {total}")
        ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
        (ARCHIVE_ROOT / "_MANIFEST.txt").write_text("\n".join(manifest_lines), encoding="utf-8")
        print(f"Manifest: {ARCHIVE_ROOT.relative_to(PROJECT_ROOT)}/_MANIFEST.txt")

    print()
    print("=" * 70)
    print(f"  Total files {'to be moved' if DRY_RUN else 'moved'}: {total}")
    print("=" * 70)


if __name__ == "__main__":
    main()