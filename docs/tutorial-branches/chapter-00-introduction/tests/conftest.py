"""
Pytest configuration for the test suite.
Adds the src directory to the Python path for imports.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
