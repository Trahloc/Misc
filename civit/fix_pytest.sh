#!/bin/bash

# PURPOSE: Fix pytest to avoid hypothesis import errors
# This script directly patches the site-packages files that cause import errors

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Identify the Python executable
PYTHON_EXEC=$(which python)
echo "Using Python: $PYTHON_EXEC"

# Run the site-packages patch script
$PYTHON_EXEC patch_site_packages.py

echo "Pytest environment has been fixed!"
echo "You can now run tests with: ./run_tests.sh"
