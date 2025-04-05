#!/bin/bash

# PURPOSE: Run pytest tests with proper configuration.
# This script provides a convenient way to run tests with consistent settings.

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Identify the Python executable
PYTHON_EXEC=$(which python)
echo "Using Python: $PYTHON_EXEC"

# Run pytest using our custom wrapper script
$PYTHON_EXEC run_pytests.py "$@"

exit $?
