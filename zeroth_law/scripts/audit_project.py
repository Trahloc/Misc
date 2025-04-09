# FILE: scripts/audit_project.py
"""Script to perform Zeroth Law compliance audit on the entire project."""

import sys
from pathlib import Path

# Add project root to sys.path to allow importing from src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.zeroth_law.analyzer.python.analyzer import analyze_file_compliance
from src.zeroth_law.file_finder import find_python_files

# TODO: Import configuration loader later


def audit_project(start_dir: Path) -> dict[Path, dict]:
    """Audits all Python files in a directory for Zeroth Law compliance.

    Args:
    ----
        start_dir: The directory to start the audit from.

    Returns:
    -------
        A dictionary mapping file paths (relative to start_dir) to their
        compliance violations. Empty dictionary value means compliant.

    """
    print(f"Starting audit in: {start_dir}")
    python_files = find_python_files(start_dir)
    print(f"Found {len(python_files)} Python files to analyze.")

    all_results: dict[Path, dict] = {}
    files_with_violations = 0

    for file_path in python_files:
        print(f". Analyzing: {file_path.relative_to(start_dir)}")
        # Use default thresholds for now
        violations = analyze_file_compliance(file_path)
        relative_path = file_path.relative_to(start_dir)
        if violations:
            all_results[relative_path] = violations
            files_with_violations += 1
            print(f"  -> Found violations: {list(violations.keys())}")
        else:
            all_results[relative_path] = {}  # Indicate compliance explicitly

    print("-" * 40)
    print("Audit Summary:")
    print(f" Total files analyzed: {len(python_files)}")
    print(f" Files with violations: {files_with_violations}")
    print(f" Compliant files: {len(python_files) - files_with_violations}")
    print("-" * 40)

    return all_results


if __name__ == "__main__":
    # Determine the root directory (assuming script is run from project root or within scripts/)
    root = project_root / "src" / "zeroth_law"  # Audit the main package for now
    # TODO: Make the target directory configurable

    results = audit_project(root)

    if any(results.values()):  # Check if any file had violations
        print("\nDetailed Violations:")
        for file, violations in results.items():
            if violations:
                print(f"\nFile: {file}")
                for category, issues in violations.items():
                    print(f"  {category.capitalize()}:")
                    for issue in issues:
                        print(f"    - {issue}")
        sys.exit(1)  # Exit with non-zero code if violations found
    else:
        print("\nProject is compliant!")
        sys.exit(0)

# <<< ZEROTH LAW FOOTER >>>
