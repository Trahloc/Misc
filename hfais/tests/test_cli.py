# FILE_LOCATION: hfais/tests/test_cli.py
"""
# PURPOSE: Tests for the CLI interface of hfais

## INTERFACES:
#   test_cli_hello: Test the CLI hello command
#   test_cli_info: Test the CLI info command
#   test_cli_verbose: Test the CLI verbose option

## DEPENDENCIES:
#   pytest
#   click.testing
#   hfais.cli
"""
import pytest
from click.testing import CliRunner
from hfais.cli import main
from hfais.hf_api import search_hf_models, cache_results, load_cached_results
from hfais.filters import filter_by_size, filter_by_creator
import os
from hfais.greeter import greet_user
import ast
from pathlib import Path

# Define the path to the cli_args.py file
CLI_ARGS_PATH = Path("src/hfais/cli_args.py")

# Define the directory to scan for other Python files
SRC_DIR = Path("src/hfais")

# Helper function to extract all function names from cli_args.py
def get_cli_args_functions():
    with CLI_ARGS_PATH.open("r") as f:
        tree = ast.parse(f.read())
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}

# Helper function to find all @click decorators in a Python file
def find_click_decorators(file_path):
    """Helper function to find all Click decorators in a Python file."""
    with file_path.open("r") as f:
        tree = ast.parse(f.read())

    click_decorators = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            # Handle cases where click is directly accessed (e.g., @click.command)
            try:
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "click":
                    click_decorators.append(node.func.attr)
            except AttributeError:
                pass
            # Handle cases where click is accessed through an attribute (e.g., from module import click)
            try:
                if isinstance(node.func.value, ast.Attribute) and node.func.value.attr == "click":
                    click_decorators.append(node.func.attr)
            except AttributeError:
                pass

    return click_decorators

# Test to flag missing abstractions in cli_args.py
@pytest.mark.parametrize("file_path", [
    path for path in SRC_DIR.rglob("*.py") if path != CLI_ARGS_PATH
])
def test_missing_cli_args_abstractions(file_path):
    cli_args_functions = get_cli_args_functions()
    click_decorators = find_click_decorators(file_path)

    for decorator in click_decorators:
        if decorator not in cli_args_functions:
            pytest.fail(f"The decorator '@click.{decorator}' in {file_path} should be abstracted into cli_args.py.")


def test_cli_hello():
    """Test the CLI hello command with different inputs"""
    runner = CliRunner()

    # Test default hello (no name provided)
    result = runner.invoke(main, ["hello"])
    assert result.exit_code == 0
    assert "Hello, world!" in result.output

    # Test hello with a name
    result = runner.invoke(main, ["hello", "Alice"])
    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output

    # Test hello with formal flag
    result = runner.invoke(main, ["hello", "--formal", "Alice"])
    assert result.exit_code == 0
    assert "Greetings, Alice!" in result.output


def test_cli_info():
    """Test the CLI info command"""
    runner = CliRunner()

    # Test basic info
    result = runner.invoke(main, ["info"])
    assert result.exit_code == 0
    assert "Project: hfais" in result.output

    # Test detailed info
    result = runner.invoke(main, ["info", "--details"])
    assert result.exit_code == 0
    assert "Project: hfais" in result.output
    assert "Description:" in result.output
    assert "Zeroth Law AI Framework" in result.output


def test_cli_verbose():
    """Test the CLI verbose option affects logging"""
    runner = CliRunner()

    # This is a simple check that the command runs with verbose flag
    # More detailed logging tests would need to capture log output
    result = runner.invoke(main, ["-v", "info"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["-vv", "info"])
    assert result.exit_code == 0


@pytest.fixture
def cli_runner():
    """Provides a Click test runner"""
    return CliRunner()


def test_cli_error_handling(cli_runner, monkeypatch):
    """Test CLI error handling when a command fails"""
    # Mock greet_user to raise an exception
    def mock_greet_user(*args, **kwargs):
        raise ValueError("Test error")

    # Apply the mock
    monkeypatch.setattr("hfais.greeter.greet_user", mock_greet_user)

    # Test that the CLI handles errors correctly
    result = cli_runner.invoke(main, ["hello"], catch_exceptions=False)
    assert result.exit_code == 1
    assert "Error" in result.output


def test_search_hf_models(monkeypatch):
    """Test the search_hf_models function."""
    def mock_get(*args, **kwargs):
        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return [{"name": "test-model", "size": 8, "creator": "test-creator"}]

        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)

    results = search_hf_models("test-query")
    assert len(results) == 1
    assert results[0]["name"] == "test-model"

def test_cache_and_load_results(tmp_path):
    """Test caching and loading of results."""
    cache_path = os.path.join(tmp_path, "cache.json")
    results = [{"name": "test-model", "size": 8, "creator": "test-creator"}]

    cache_results(results, cache_path)
    loaded_results = load_cached_results(cache_path)

    assert len(loaded_results) == 1
    assert loaded_results[0]["name"] == "test-model"

def test_filter_by_size():
    """Test filtering by size."""
    models = [
        {"name": "small-model", "size": 2},
        {"name": "large-model", "size": 10},
    ]

    filtered = filter_by_size(models, min_size=5, max_size=15)
    assert len(filtered) == 1
    assert filtered[0]["name"] == "large-model"

def test_filter_by_creator():
    """Test filtering by creator."""
    models = [
        {"name": "model-a", "creator": "Alice"},
        {"name": "model-b", "creator": "Bob"},
    ]

    filtered = filter_by_creator(models, creator="Alice")
    assert len(filtered) == 1
    assert filtered[0]["name"] == "model-a"