# FILE: tests/test_cli.py
"""Tests for the command-line interface (cli.py)."""

import os
import subprocess
import sys
from pathlib import Path


# Helper to run the CLI script via subprocess
def run_cli(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Runs the zeroth-law script as a subprocess using the installed script path."""
    env_bin_dir = Path(sys.executable).parent
    script_path = env_bin_dir / "zeroth-law"
    if not script_path.exists():
        raise FileNotFoundError(f"zeroth-law script not found in {env_bin_dir}")

    command = [str(script_path)] + args
    process_env = os.environ.copy()

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd or Path.cwd(),
        env=process_env,
    )


# Common compliant content for __init__.py in tests
INIT_PY_CONTENT = """# FILE: __init__.py
\"\"\"Test Source Package Init.\"\"\"
# <<< ZEROTH LAW FOOTER >>>
"""


# Test Case 1: Default Output (No Flags)
def test_cli_default_output(tmp_path: Path) -> None:
    """Test the default output level (expect INFO like behavior)."""
    # Arrange
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text(INIT_PY_CONTENT)
    compliant_content = """# FILE: src/compliant.py
\"\"\"Module docstring.\"\"\"
# <<< ZEROTH LAW FOOTER >>>
"""
    (tmp_path / "src" / "compliant.py").write_text(compliant_content)
    (tmp_path / "pyproject.toml").touch()

    # Act
    result = run_cli(["src"], cwd=tmp_path)

    # Assert
    assert result.returncode == 0
    assert "Starting audit" in result.stderr
    assert "Found 2 Python files" in result.stderr
    assert "Using configuration" in result.stderr
    assert "Audit Summary" in result.stderr
    assert "Compliant files: 2" in result.stderr
    assert "Project is compliant!" in result.stderr
    assert "Analyzing:" not in result.stderr
    assert result.stdout == ""


# Test Case 2: Quiet Output (-q)
def test_cli_quiet_output(tmp_path: Path) -> None:
    """Test the quiet output level (-q)."""
    # Arrange
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text(INIT_PY_CONTENT)
    non_compliant_content = """# FILE: src/bad.py
\"\"\"Module docstring.\"\"\"
# No footer here
"""
    (tmp_path / "src" / "bad.py").write_text(non_compliant_content)
    pyproject_content = """[tool.poetry]
name = "test"
version = "0.1.0"
description = ""
authors = [""]
[tool.zeroth-law]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    # Act
    result = run_cli(["-q", "src"], cwd=tmp_path)

    # Assert
    assert result.returncode == 1
    assert "Starting audit" not in result.stderr
    assert "Found 2 Python files" not in result.stderr
    assert "Analyzing:" not in result.stderr
    assert "-> Violations found in bad.py: ['footer']" in result.stderr
    assert "Audit Summary" in result.stderr
    assert "Files with violations: 1" in result.stderr
    assert "Detailed Violations:" in result.stderr
    assert "File: bad.py" in result.stderr
    assert result.stdout == ""


# Test Case 3: Debug Output (-vv)
def test_cli_debug_output(tmp_path: Path) -> None:
    """Test the debug output level (-vv)."""
    # Arrange
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text(INIT_PY_CONTENT)
    compliant_content = """# FILE: src/compliant.py
\"\"\"Module docstring.\"\"\"
# <<< ZEROTH LAW FOOTER >>>
"""
    (tmp_path / "src" / "compliant.py").write_text(compliant_content)
    (tmp_path / "pyproject.toml").touch()

    # Act
    result = run_cli(["-vv", "src"], cwd=tmp_path)

    # Assert
    assert result.returncode == 0
    assert "Starting audit" in result.stderr
    assert "Found 2 Python files" in result.stderr
    assert "Analyzing: __init__.py" in result.stderr
    assert "Analyzing: compliant.py" in result.stderr
    assert "Audit Summary" in result.stderr
    assert "Compliant files: 2" in result.stderr
    assert "Project is compliant!" in result.stderr
    assert result.stdout == ""


# TODO: Add test_cli_verbose_output (might be same as default for now)
# TODO: Add test_cli_version
# TODO: Add test_cli_file_not_found

# <<< ZEROTH LAW FOOTER >>>
