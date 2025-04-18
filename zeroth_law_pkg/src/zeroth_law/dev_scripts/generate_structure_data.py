# src/zeroth_law/dev_scripts/generate_structure_data.py
import argparse
import json
import sys
from pathlib import Path

# --- Configuration ---
# (Mirrors the exclusions in test_project_structure.py for consistency)
# Files/patterns to exclude from the source code listing
SRC_EXCLUDE_PATTERNS = [
    "__init__.py",
    "__main__.py",
    "cli.py",
    "dev_scripts/",
    "tools/",
    # Add other patterns if needed
]


# --- Helper ---
def _is_excluded(path: Path, exclude_patterns: list[str], base_dir: Path) -> bool:
    """Check if a path matches any exclusion patterns relative to a base dir."""
    # Ensure path is relative to base_dir for consistent checking
    try:
        relative_path = path.relative_to(base_dir)
    except ValueError:
        # Path is not inside base_dir, exclude it
        return True

    relative_path_str = str(relative_path)

    for pattern in exclude_patterns:
        if pattern.endswith("/"):  # Directory pattern
            # Check if the path starts with the directory pattern
            # Add trailing slash to relative path for prefix check if needed
            dir_prefix = pattern.rstrip("/")
            if relative_path_str.startswith(dir_prefix + "/") or relative_path_str == dir_prefix:
                return True
        elif pattern == Path(relative_path_str).name:  # Filename pattern
            return True
        # Note: Path.match does not work well with relative paths directly here
        # Stick to name and directory prefix matching for simplicity now.
        # elif path.match(pattern): # Glob pattern could be added if needed
        #     return True
    return False


# --- Main Logic ---
def main():
    parser = argparse.ArgumentParser(description="Generate project structure data (currently just source files).")
    parser.add_argument("--output", required=True, help="Path to output JSON file.")
    parser.add_argument("--source-base", required=True, help="Path to the base 'src' directory.")
    args = parser.parse_args()

    output_path = Path(args.output)
    source_base_path = Path(args.source_base).resolve()  # Resolve to absolute path
    target_src_dir = source_base_path / "zeroth_law"  # Specific target

    if not target_src_dir.is_dir():
        print(f"Error: Target source directory not found: {target_src_dir}", file=sys.stderr)
        sys.exit(1)

    source_files = []
    for path in target_src_dir.rglob("*.py"):
        # Check exclusions relative to target_src_dir
        if not _is_excluded(path, SRC_EXCLUDE_PATTERNS, target_src_dir):
            # Store path relative to the *parent* of source_base_path
            # (e.g., "src/zeroth_law/module.py")
            try:
                # Use source_base_path.parent as the base for relativity
                relative_to_project_root = path.relative_to(source_base_path.parent)
                source_files.append(str(relative_to_project_root))
            except ValueError:
                print(f"Warning: Could not make path relative to source base parent: {path}", file=sys.stderr)

    output_data = {"schema_version": "1.0_file_list", "source_files": sorted(source_files)}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Successfully generated structure data to {output_path}")


if __name__ == "__main__":
    main()
