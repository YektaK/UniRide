import sys
import os

# Ensure the project root is on sys.path so that
# `from academic_benchmark ...` and `from sota_tsp ...` resolve correctly.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
