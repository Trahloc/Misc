"""
# PURPOSE: Test import analysis functionality

## INTERFACES:
  - test_used_imports: Verify that used imports don't trigger penalties
  - test_unused_imports: Verify that unused imports are detected and penalized
  - test_mixed_imports: Verify handling of both used and unused imports

## DEPENDENCIES:
    pytest
    ast
    pathlib
"""

import ast
from pathlib import Path
import pytest
from zeroth_law.metrics.imports import calculate_import_metrics


def test_used_imports():
    """Test that used imports don't trigger penalties."""
    # Create a sample AST with used imports
    source = """
import os
import sys

def test():
    print(os.path.join("test", "path"))
    print(sys.version)
"""
    tree = ast.parse(source)
    metrics = calculate_import_metrics(tree)

    assert metrics["import_count"] == 0
    assert metrics["imports_score"] == 100


def test_unused_imports():
    """Test that unused imports are detected and penalized."""
    # Create a sample AST with unused imports
    source = """
import os
import sys
import json
import re

def test():
    print("Hello")
"""
    tree = ast.parse(source)
    metrics = calculate_import_metrics(tree)

    assert metrics["import_count"] == 4  # All imports are unused
    assert metrics["imports_score"] == 60  # 100 - (4 * 10)


def test_mixed_imports():
    """Test handling of both used and unused imports."""
    # Create a sample AST with both used and unused imports
    source = """
import os
import sys
import json  # unused
import re    # unused

def test():
    print(os.path.join("test", "path"))
    print(sys.version)
"""
    tree = ast.parse(source)
    metrics = calculate_import_metrics(tree)

    assert metrics["import_count"] == 2  # Only json and re are unused
    assert metrics["imports_score"] == 80  # 100 - (2 * 10)
