"""
Pytest configuration for optimizer_api tests
"""

import sys
import os

# Add the optimizer_api directory to Python path
test_dir = os.path.dirname(os.path.abspath(__file__))
if test_dir not in sys.path:
    sys.path.insert(0, test_dir)
