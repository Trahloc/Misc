# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/tests/test_analyzer.py (CORRECTED)
"""
# PURPOSE: Tests for the Zeroth Law analyzer.

## INTERFACES:
 - All test functions

## DEPENDENCIES:
 - pytest
 - zeroth_law.analyzer
 - zeroth_law.exceptions
"""
import pytest
import os
from zeroth_law.analyzer import analyze_file, analyze_directory, generate_footer, should_ignore
from zeroth_law.exceptions import FileNotFoundError, NotPythonFileError, AnalysisError

# Create a temporary directory for test files
TEST_DIR = "test_files"

@pytest.fixture(scope="session", autouse=True)
def create_test_files():
    """Creates temporary test files and directories."""
    os.makedirs(TEST_DIR, exist_ok=True)

    # Create test directories including dot-prefixed ones
    os.makedirs(os.path.join(TEST_DIR, ".old"), exist_ok=True)
    os.makedirs(os.path.join(TEST_DIR, "src"), exist_ok=True)
    os.makedirs(os.path.join(TEST_DIR, "__pycache__"), exist_ok=True)

    # Create a valid Python file
    with open(os.path.join(TEST_DIR, "valid_file.py"), "w") as f:
        f.write('''"""Docstring"""\ndef my_function():\n    pass\n\n"""Footer"""''')

    # Create a file in .old directory
    with open(os.path.join(TEST_DIR, ".old", "old_file.py"), "w") as f:
        f.write('''"""Old file"""\ndef old_function():\n    pass''')

    # Create a file in __pycache__ directory
    with open(os.path.join(TEST_DIR, "__pycache__", "cached.pyc"), "w") as f:
        f.write("cache data")

    # Create a file with a syntax error
    with open(os.path.join(TEST_DIR, "syntax_error.py"), "w") as f:
        f.write("def my_function(:\n    pass")  # Invalid syntax

    # Create an empty file
    with open(os.path.join(TEST_DIR, "empty_file.py"), "w") as f:
        pass

    # Create a non-Python file
    with open(os.path.join(TEST_DIR, "not_a_python_file.txt"), "w") as f:
        f.write("This is not a Python file.")

    yield  # This allows the tests to run

    # Teardown: Remove the test directory and its contents
    for root, sub_dirs, files in os.walk(TEST_DIR, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in sub_dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(TEST_DIR)

def test_should_ignore_dot_directory():
    """Test that dot-prefixed directories are properly ignored."""
    base_path = TEST_DIR
    patterns = ["**/.old/**"]

    # Test .old directory
    file_path = os.path.join(TEST_DIR, ".old", "old_file.py")
    assert should_ignore(file_path, base_path, patterns), "Should ignore files in .old directory"

    # Test non-dot directory
    file_path = os.path.join(TEST_DIR, "src", "file.py")
    assert not should_ignore(file_path, base_path, patterns), "Should not ignore files in normal directories"

def test_should_ignore_cached_files():
    """Test that cache directories and files are properly ignored."""
    base_path = TEST_DIR
    patterns = ["**/__pycache__/**", "**/*.pyc"]

    # Test __pycache__ directory
    file_path = os.path.join(TEST_DIR, "__pycache__", "cached.pyc")
    assert should_ignore(file_path, base_path, patterns), "Should ignore files in __pycache__ directory"

    # Test .pyc file in regular directory
    file_path = os.path.join(TEST_DIR, "module.pyc")
    assert should_ignore(file_path, base_path, patterns), "Should ignore .pyc files"

def test_should_ignore_with_multiple_patterns():
    """Test that multiple ignore patterns work correctly."""
    base_path = TEST_DIR
    patterns = ["**/.old/**", "**/__pycache__/**", "**/*.pyc", "**/.git/**"]

    # Test various paths against multiple patterns
    assert should_ignore(os.path.join(TEST_DIR, ".old", "file.py"), base_path, patterns)
    assert should_ignore(os.path.join(TEST_DIR, "__pycache__", "file.pyc"), base_path, patterns)
    assert should_ignore(os.path.join(TEST_DIR, "module.pyc"), base_path, patterns)
    assert should_ignore(os.path.join(TEST_DIR, ".git", "objects", "file"), base_path, patterns)
    assert not should_ignore(os.path.join(TEST_DIR, "src", "file.py"), base_path, patterns)

def test_should_ignore_relative_paths():
    """Test that relative paths are handled correctly."""
    base_path = TEST_DIR
    patterns = ["**/.old/**"]

    # Test with different path formats
    assert should_ignore(os.path.join(TEST_DIR, ".old", "file.py"), base_path, patterns)
    assert should_ignore(os.path.join(TEST_DIR, ".old/file.py"), base_path, patterns)
    assert should_ignore(".old/file.py", TEST_DIR, patterns)

def test_analyze_valid_file():
    """Tests analyzing a valid Python file."""
    metrics = analyze_file(os.path.join(TEST_DIR, "valid_file.py"))
    assert "error" not in metrics
    assert metrics["file_name"] == "valid_file.py"
    assert metrics["overall_score"] > 0  # Expect a positive score


def test_analyze_file_not_found():
    """Tests handling of a non-existent file."""
    with pytest.raises(FileNotFoundError):
        analyze_file("nonexistent_file.py")


def test_analyze_not_python_file():
    """Tests handling of a non-Python file."""
    with pytest.raises(NotPythonFileError):
        analyze_file(os.path.join(TEST_DIR, "not_a_python_file.txt"))

def test_analyze_syntax_error():
    """Tests handling of a file with a syntax error."""
    with pytest.raises(AnalysisError) as e:
        analyze_file(os.path.join(TEST_DIR, "syntax_error.py"))
    assert "Syntax error" in str(e.value)

def test_analyze_directory_not_found():
    with pytest.raises(FileNotFoundError):
        analyze_directory("non_existent_directory", False, False, None)

def test_generate_footer():
    """Tests the generate_footer function."""
    metrics = {
        "overall_score": 85,
        "compliance_level": "Good",
        "penalties": [{"reason": "Test Penalty", "deduction": 5}],
    }
    footer = generate_footer(metrics)
    assert "ZEROTH LAW COMPLIANCE:" in footer
    assert "Overall Score: 85/100 - Good" in footer
    assert "Test Penalty: -5" in footer
    assert "Analysis Timestamp:" in footer  # Check for timestamp