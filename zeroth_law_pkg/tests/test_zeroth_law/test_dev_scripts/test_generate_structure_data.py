# tests/test_generate_structure_data.py
import json
import subprocess
import sys
from pathlib import Path

# --- Configuration ---
try:
    WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
except NameError:
    WORKSPACE_ROOT = Path.cwd().resolve()

GENERATION_SCRIPT_PATH = WORKSPACE_ROOT / "src" / "zeroth_law" / "dev_scripts" / "generate_structure_data.py"
TEST_SRC_SUBDIR = Path("src") / "zeroth_law"


def test_generate_structure_data_basic(tmp_path):
    """Test basic structure data generation."""
    # Setup dummy project structure
    src_dir = tmp_path / TEST_SRC_SUBDIR
    src_dir.mkdir(parents=True)
    output_json = tmp_path / "structure_output.json"

    # Files that should be included
    (src_dir / "module_a.py").touch()
    (src_dir / "subdir").mkdir()
    (src_dir / "subdir" / "module_b.py").touch()

    # Files/Dirs that should be excluded by the script's internal logic
    (src_dir / "__init__.py").touch()
    (src_dir / "cli.py").touch()  # Assuming cli.py is usually excluded
    (src_dir / "tools").mkdir()
    (src_dir / "tools" / "config.py").touch()
    (src_dir / "dev_scripts").mkdir()
    (src_dir / "dev_scripts" / "helper.py").touch()
    (tmp_path / TEST_SRC_SUBDIR / ".." / "other_src_file.py").touch()  # File outside src/zeroth_law
    (src_dir / "data.txt").touch()  # Non-python file

    # Expected relative paths (relative to workspace root for consistency)
    expected_files = sorted(
        [
            str(TEST_SRC_SUBDIR / "module_a.py"),
            str(TEST_SRC_SUBDIR / "subdir" / "module_b.py"),
        ]
    )

    # Run the script
    cmd = [
        sys.executable,
        str(GENERATION_SCRIPT_PATH),
        "--output",
        str(output_json),
        "--source-base",
        str(tmp_path / "src"),  # Tell script where src starts
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=tmp_path)

    print("Script STDOUT:", result.stdout)
    print("Script STDERR:", result.stderr)
    assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
    assert output_json.is_file(), "Output JSON file was not created"

    # Verify JSON content
    with open(output_json, "r") as f:
        data = json.load(f)

    assert "source_files" in data, "JSON missing 'source_files' key"
    # Sort actual paths before comparing
    actual_files = sorted(data["source_files"])
    assert actual_files == expected_files, "List of source files in JSON does not match expected"


# --- Test Script Implementation (Placeholder) ---
# We need the actual script file to exist for the test runner
# I'll create a placeholder script now.
