#!/usr/bin/env python3
"""
Create a new executable civit-debug script that uses our updated CLI.
This is an alternative approach if the update_cli.py doesn't work.
"""
import os
import sys
import stat
from pathlib import Path


def create_debug_script():
    """Create a new executable script that uses our updated CLI"""
    # Find the conda environment bin directory
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if not conda_prefix:
        print("CONDA_PREFIX environment variable not found.")
        print("Run this script from within your conda environment.")
        return False

    bin_dir = Path(conda_prefix) / "bin"
    if not bin_dir.exists():
        print(f"Bin directory not found: {bin_dir}")
        return False

    # Get the path to the current script directory
    script_dir = Path(__file__).parent

    # Create the new executable script
    new_script = bin_dir / "civit-debug"
    script_content = f"""#!/usr/bin/env python3
# civit-debug - Debug version of the civit CLI
import os
import sys

# Add the source directory to the Python path
sys.path.insert(0, "{script_dir}")

# Import our custom CLI implementation
from src.main import main

if __name__ == "__main__":
    sys.exit(main())
"""

    try:
        with open(new_script, "w") as f:
            f.write(script_content)

        # Make the script executable
        st = os.stat(new_script)
        os.chmod(new_script, st.st_mode | stat.S_IEXEC)

        print(f"Created executable debug script: {new_script}")
        print("You can now run: civit-debug -d URL")
        return True

    except Exception as e:
        print(f"Failed to create debug script: {e}")
        return False


if __name__ == "__main__":
    if create_debug_script():
        print("\nCreation of debug script successful!")
    else:
        print("\nFailed to create debug script.")
        sys.exit(1)
