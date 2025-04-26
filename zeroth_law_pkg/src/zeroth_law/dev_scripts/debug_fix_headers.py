"""Debug script to fix header/footer for a specific file and log comparison."""

import logging
import sys
from pathlib import Path

# Add project root to sys.path BEFORE attempting src import
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve() # Go up 3 levels: dev_scripts -> zeroth_law -> src
sys.path.insert(0, str(PROJECT_ROOT.parent)) # Add the directory containing 'src'

# Import the function to test
from src.zeroth_law.analyzer.python.analyzer import check_header_compliance  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Define paths (relative to project root determined above)
TARGET_FILE = PROJECT_ROOT / "__init__.py" # Target src/zeroth_law/__init__.py
COMPARISON_DIR = PROJECT_ROOT.parent / ".ruff_cache"  # Use existing ignored dir in workspace root
COMPARISON_FILE = COMPARISON_DIR / "debug_src_init_expected.py"
BACKUP_FILE = COMPARISON_DIR / "debug_src_init_backup.py"

# Define intended content
INTENDED_CONTENT = """# FILE: src/zeroth_law/__init__.py
\"\"\"Zeroth Law Audit Tool Package.\"\"\"

# <<< ZEROTH LAW FOOTER >>>
"""


def main() -> None:
    """Reads target, writes comparison, attempts fix if needed."""
    log.info(f"Debugging header/footer fix for: {TARGET_FILE.relative_to(PROJECT_ROOT)}")

    # Ensure comparison directory exists
    try:
        COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
        log.info(f"Ensured comparison directory exists: {COMPARISON_DIR.relative_to(PROJECT_ROOT.parent)}")
    except OSError as e:
        log.error(f"Could not create comparison directory {COMPARISON_DIR}: {e}")
        return

    # Write intended content to comparison file
    try:
        COMPARISON_FILE.write_text(INTENDED_CONTENT, encoding="utf-8")
        log.info(f"Wrote intended content to comparison file: {COMPARISON_FILE.relative_to(PROJECT_ROOT.parent)}")
    except OSError as e:
        log.error(f"Could not write to comparison file {COMPARISON_FILE}: {e}")
        # Continue to check the original file anyway

    # Read current content of target file
    current_content = ""
    try:
        if TARGET_FILE.exists():
            current_content = TARGET_FILE.read_text(encoding="utf-8")
            log.info(f"Successfully read current content from: {TARGET_FILE.relative_to(PROJECT_ROOT)}")
        else:
            log.warning(f"Target file does not exist: {TARGET_FILE.relative_to(PROJECT_ROOT)}")
            # If it doesn't exist, we definitely want to write it
            current_content = ""  # Treat as empty for comparison
    except OSError as e:
        log.error(f"Could not read target file {TARGET_FILE}: {e}")
        return  # Cannot proceed without reading the target

    # Compare and attempt fix
    if current_content == INTENDED_CONTENT:
        log.info("Target file content already matches intended content. No action needed.")
    else:
        log.warning("Target file content differs from intended content.")
        log.info("--- Current Content ---")
        log.info(repr(current_content))  # Use repr to show hidden chars like \r
        log.info("--- Intended Content ---")
        log.info(repr(INTENDED_CONTENT))
        log.info("-----------------------")

        # Save a backup of the current content before modifying
        try:
            BACKUP_FILE.write_text(current_content, encoding="utf-8")
            log.info(f"Saved backup of original content to: {BACKUP_FILE.relative_to(PROJECT_ROOT.parent)}")
        except OSError as e:
            log.error(f"Could not save backup file {BACKUP_FILE}: {e}")
            # Optionally, decide whether to abort the fix attempt if backup fails
            # For now, we'll continue and just log the backup error

        log.info("Attempting to write intended content to target file...")
        try:
            TARGET_FILE.write_text(INTENDED_CONTENT, encoding="utf-8", newline="\n")  # Enforce LF line endings
            log.info("Successfully wrote intended content to target file.")
            # Verify write
            verify_content = TARGET_FILE.read_text(encoding="utf-8")
            if verify_content == INTENDED_CONTENT:
                log.info("Verification successful: Target file content matches intended content after write.")
            else:
                log.error("Verification FAILED: Target file content DOES NOT match intended content after write.")
                log.error(f"Content after write: {verify_content!r}")

        except OSError as e:
            log.error(f"FAILED to write intended content to target file {TARGET_FILE}: {e}")

    # --- Add Direct Check --- #
    log.info("Performing direct header check on files...")

    # Check the expected content file
    try:
        expected_violations = check_header_compliance(COMPARISON_FILE)
        log.info(f"check_header_compliance({COMPARISON_FILE.name}) result: {expected_violations or '[] (Compliant)'}")
    except Exception as e:
        log.error(f"Error running check_header_compliance on {COMPARISON_FILE.name}: {e}")

    # Check the actual target file
    try:
        if TARGET_FILE.exists():
            actual_violations = check_header_compliance(TARGET_FILE)
            log.info(f"check_header_compliance({TARGET_FILE.name}) result: {actual_violations or '[] (Compliant)'}")
        else:
            log.warning(f"Skipping direct check on {TARGET_FILE.name} as it doesn't exist.")
    except Exception as e:
        log.error(f"Error running check_header_compliance on {TARGET_FILE.name}: {e}")


if __name__ == "__main__":
    main()

# <<< ZEROTH LAW FOOTER >>>