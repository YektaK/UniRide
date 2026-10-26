"""Command line verifier for run campaigns (Gate D, D-02).

``python -m academic_benchmark.studies.verify_manifests DIR [DIR ...]`` recomputes the checksums of each campaign directory
(index, manifests, result files), cross-checks manifests against the index and result rows, and exits 0 only when every
directory verifies. It reads files only: no solver runs and nothing is written.
"""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

from academic_benchmark.analysis.manifests import verify_campaign_detailed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify run manifests, the campaign index and result checksums")
    parser.add_argument("directories", nargs="+", help="campaign output directories (each holds run_index.json)")
    parser.add_argument(
        "--repository-root", default=None,
        help="repository checked out at the campaign commit, to compare the recorded profile and analysis-plan hashes with its files "
             "(default: the repository this code lives in)",
    )
    args = parser.parse_args(argv)
    failed = False
    for directory in args.directories:
        result = verify_campaign_detailed(directory, repository_root=args.repository_root)
        if result.ok:
            print(f"OK {directory}: {result.checked} run manifest(s) verified")
            for note in result.notes:
                print(f"  NOTE {note}")
            continue
        failed = True
        print(f"FAIL {directory}: {len(result.errors)} problem(s)")
        for error in result.errors:
            print(f"  {error}")
        for note in result.notes:
            print(f"  NOTE {note}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
