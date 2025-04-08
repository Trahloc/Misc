#!/bin/bash
set -euo pipefail # Strict mode

# Ensure script is run from project root
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
cd "$PROJECT_ROOT"

echo "Generating requirements.txt and requirements-dev.txt from pyproject.toml using poetry export..."

# Ensure poetry is available
if ! command -v poetry &> /dev/null; then
    echo "Error: poetry command could not be found."
    echo "Ensure it is installed in the environment used to run this script (e.g., localbin)."
    exit 1
fi

# Ensure poetry-plugin-export is available (or installed via poetry)
# Simple check: See if export command exists
if ! poetry export --help &> /dev/null; then
    echo "Error: poetry export command not found. Is poetry-plugin-export installed?"
    echo "Attempting to install/update it: pip install --upgrade poetry-plugin-export"
    pip install --upgrade poetry-plugin-export || exit 1
fi

# Optional: Run poetry lock first to ensure lock file is up-to-date
echo "Running poetry lock to update lock file..."
poetry lock --no-update # Use --no-update if you only want to ensure consistency, not resolve anew

# Generate requirements files
echo "Exporting main dependencies to requirements.txt..."
poetry export --without-hashes -o requirements.txt

echo "Exporting development dependencies to requirements-dev.txt..."
poetry export --without-hashes --only dev -o requirements-dev.txt

echo "Requirements files generated successfully."
