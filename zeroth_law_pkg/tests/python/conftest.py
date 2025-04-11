# File: tests/python/conftest.py
"""Configuration for pytest to set up Python path correctly."""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
