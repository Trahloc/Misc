#!/bin/bash
# PURPOSE: Aggregates all # TODO: comments and # noqa: E402 suppressions
#          from src/ and tests/ into CODE_TODOS.md
# Creates a read-only dashboard view for human convenience.

# echo "DEBUG: generate_code_todos.sh starting..."

set -e # Exit immediately if a command exits with a non-zero status.
set -o pipefail # Exit status of the last command that threw a non-zero exit code is returned.

# Determine Git root directory reliably
GIT_ROOT=$(git rev-parse --show-toplevel)
if [ -z "${GIT_ROOT}" ]; then
    echo "Error: Failed to determine Git repository root." >&2
    exit 1
fi
# echo "DEBUG: Git root detected as: ${GIT_ROOT}"

PROJECT_SUBDIR="zeroth_law_pkg"
# Define output file path relative to determined Git root
OUTPUT_FILE="${GIT_ROOT}/${PROJECT_SUBDIR}/CODE_TODOS.md"
# Define search directories relative to determined Git root
# NOTE: Search dev_scripts as well now
SEARCH_DIRS=("${GIT_ROOT}/${PROJECT_SUBDIR}/src" "${GIT_ROOT}/${PROJECT_SUBDIR}/tests" "${GIT_ROOT}/${PROJECT_SUBDIR}/src/zeroth_law/dev_scripts")

RG_PATH="$HOME/.local/share/cargo/bin/rg"
TMP_RG_OUT="${GIT_ROOT}/${PROJECT_SUBDIR}/rg_output.tmp"

# Check if rg is installed at the specified path relative to HOME
if ! command -v "${RG_PATH}" &> /dev/null
then
    echo "Error: ripgrep (rg) not found at expected path: ${RG_PATH}" >&2
    exit 1
fi

# echo "DEBUG: Writing header section to ${OUTPUT_FILE}"
# Create or clear the output file and write the initial static header
echo "# Code-Level Issues & TODOs (Auto-Generated)" > "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"
echo "Generated: $(date --iso-8601=seconds)" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"

# Step 1: Run rg and save raw output to temp file
# Search for lines containing either '# TODO:' or '# noqa: E402'
# echo "DEBUG: Running rg, searching ${SEARCH_DIRS[*]}, outputting to ${TMP_RG_OUT}"
"${RG_PATH}" --no-heading --line-number --glob '*.py' --glob '*.sh' --regexp '# (TODO:|noqa: E402)' "${SEARCH_DIRS[@]}" > "${TMP_RG_OUT}" || echo "Warning: rg found no relevant comments or failed. Exit code: $?"

# Step 1.5: Sort the temporary file alphabetically by path:line
# echo "DEBUG: Sorting ${TMP_RG_OUT}"
sort "${TMP_RG_OUT}" -o "${TMP_RG_OUT}"

# Step 2: Process temp file with awk for formatted table and append to final output
# echo "DEBUG: Running awk on ${TMP_RG_OUT}, appending formatted table to ${OUTPUT_FILE}"
if [ -s "${TMP_RG_OUT}" ]; then # Check if temp file is not empty
    # Pass GIT_ROOT and PROJECT_SUBDIR to awk to remove the correct prefix
    # The awk script reads all lines, calculates widths, then prints formatted table
    awk -F':' -v git_root="${GIT_ROOT}/" -v proj_subdir="${PROJECT_SUBDIR}/" '
    # BEGIN block: Define FS, initialize max widths with header lengths
    BEGIN {
        max_path = length("Source");
        max_line = length("Line");
        max_issue = length("Issue / TODO"); # Renamed header
        git_root_prefix = git_root proj_subdir; # Construct combined prefix
        if (substr(git_root_prefix, length(git_root_prefix)) != "/") {
             git_root_prefix = git_root_prefix "/"; # Ensure trailing slash
        }
    }

    # Main block: Process each line from rg output
    {
        path = $1;
        sub(git_root_prefix, "", path); # Remove prefix

        line_num = $2;

        # Determine comment/issue text based on matched pattern
        if (index($0, "# TODO:")) {
            issue_text = substr($0, index($0, "# TODO:") + length("# TODO:"));
            sub(/^[ \t]+/, "", issue_text); # Remove leading space
        } else if (index($0, "# noqa: E402")) {
            issue_text = "[Suppressed] Module import not at top of file (E402)";
        } else {
            # Extract the full line content after the line number colon as fallback
            full_line_content = substr($0, length($1) + length($2) + 2); # +2 for the two colons
            issue_text = "Unknown pattern: " full_line_content;
        }

        # Store data
        paths[NR] = path;
        lines[NR] = line_num;
        issues[NR] = issue_text; # Use new array name

        # Update max widths
        if (length(path) > max_path) max_path = length(path);
        if (length(line_num) > max_line) max_line = length(line_num);
        if (length(issue_text) > max_issue) max_issue = length(issue_text); # Update max width for the issue column
    }

    # END block: Print formatted table
    END {
        padding = 1
        max_path += padding;
        max_line += padding;
        # No padding needed for the last column text width itself,
        # but the separator width needs to be based on the max content width (max_issue).

        # Print Header
        printf "%-*s | %-*s | %s\n",
               max_path, "Source",
               max_line, "Line",
               "Issue / TODO"; # New header

        # Print Separator line
        sep_path = sprintf("%-*s", max_path, ""); gsub(/ /, "-", sep_path);
        sep_line = sprintf("%-*s", max_line, ""); gsub(/ /, "-", sep_line);
        # Calculate separator width for the last column based on its max content width
        sep_issue = sprintf("%-*s", max_issue, ""); gsub(/ /, "-", sep_issue);
        printf "%s-|-%s-|-%s\n", sep_path, sep_line, sep_issue;

        # Print Data Rows
        for (i = 1; i <= NR; i++) {
            printf "%-*s | %-*s | %s\n",
                   max_path, paths[i],
                   max_line, lines[i],
                   issues[i]; # Use new array
        }
    }
    ' "${TMP_RG_OUT}" >> "${OUTPUT_FILE}" || echo "awk command failed! Exit code: $?"

else
    # If no issues found, print placeholder table
    echo "Source | Line | Issue / TODO" >> "${OUTPUT_FILE}"
    echo "-------|------|--------------" >> "${OUTPUT_FILE}"
    echo "(No TODOs or suppressed E402 found)" >> "${OUTPUT_FILE}"
fi
# echo "DEBUG: awk processing finished."

# Step 3: Clean up temp file
rm -f "${TMP_RG_OUT}"
# echo "DEBUG: Cleaned up temp file."

echo "" >> "${OUTPUT_FILE}"
echo "NOTE: This file is auto-generated by src/zeroth_law/dev_scripts/generate_code_todos.sh. Do not edit directly." >> "${OUTPUT_FILE}"

echo "Generated ${OUTPUT_FILE}" # Final script output for hook runner