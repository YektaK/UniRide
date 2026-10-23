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
    args = parser.parse_args(argv)
    failed = False
    for directory in args.directories:
        result = verify_campaign_detailed(directory)
        if result.ok:
            print(f"OK {directory}: {result.checked} run manifest(s) verified")
            continue
        failed = True
        print(f"FAIL {directory}: {len(result.errors)} problem(s)")
        for error in result.errors:
            print(f"  {error}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
