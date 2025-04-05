#!/usr/bin/env python
"""
Audit test files to find potential unmocked network calls.

Usage: python -m scripts.audit_test_network
"""
import os
import re
from pathlib import Path


NETWORK_CALL_PATTERNS = [
    r"requests\.(get|post|put|delete|head)\(",
    r"urllib\.(request|urlopen)",
    r"http\.(client|HTTPConnection)",
]

MOCK_PATTERNS = [
    r'mock\.patch\([\'"]requests\.',
    r"mock_requests",
    r'@pytest\.mark\.usefixtures\([\'"]mock_requests[\'"]',
    r'@mock\.patch\([\'"]requests\.',
]


def is_test_file(file_path):
    """Check if the file is a test file."""
    return file_path.name.startswith("test_") and file_path.suffix == ".py"


def find_test_files(base_dir):
    """Find all test files in the project."""
    base_path = Path(base_dir)
    test_files = []
    for path in base_path.rglob("*.py"):
        if is_test_file(path):
            test_files.append(path)
    return test_files


def check_file_for_unmocked_network_calls(file_path):
    """Check a test file for potential unmocked network calls."""
    with open(file_path, "r") as f:
        content = f.read()

    # Check if the file contains network calls
    has_network_calls = any(
        re.search(pattern, content) for pattern in NETWORK_CALL_PATTERNS
    )

    # Check if the network calls are mocked
    has_mocks = any(re.search(pattern, content) for pattern in MOCK_PATTERNS)

    if has_network_calls and not has_mocks:
        return True
    return False


def main():
    """Main function to audit test files."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_files = find_test_files(base_dir)

    risky_files = []
    for file_path in test_files:
        if check_file_for_unmocked_network_calls(file_path):
            risky_files.append(file_path)

    if risky_files:
        print(
            f"Found {len(risky_files)} test files with potential unmocked network calls:"
        )
        for file_path in risky_files:
            rel_path = os.path.relpath(file_path, base_dir)
            print(f"  - {rel_path}")
        print(
            "\nRecommendation: Add proper mocking using @pytest.fixture('mock_requests') or @mock.patch"
        )
        return 1
    else:
        print("No unmocked network calls detected in test files.")
        return 0


if __name__ == "__main__":
    exit(main())
