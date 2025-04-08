#!/bin/bash
# PURPOSE: Aggregates all # TODO: comments from src/ and tests/ into CODE_TODOS.md
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

PROJECT_SUBDIR="zeroth_law"
# Define output file path relative to determined Git root
OUTPUT_FILE="${GIT_ROOT}/${PROJECT_SUBDIR}/CODE_TODOS.md"
# Define search directories relative to determined Git root
SEARCH_DIRS=("${GIT_ROOT}/${PROJECT_SUBDIR}/src" "${GIT_ROOT}/${PROJECT_SUBDIR}/tests")

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
echo "# Code-Level TODOs (Auto-Generated)" > "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"
echo "Generated: $(date --iso-8601=seconds)" >> "${OUTPUT_FILE}"
echo "" >> "${OUTPUT_FILE}"

# Step 1: Run rg and save raw output to temp file
# echo "DEBUG: Running rg, searching ${SEARCH_DIRS[*]}, outputting to ${TMP_RG_OUT}"
# Use --no-config and --ignore-case=false for consistent results if needed
"${RG_PATH}" --no-heading --line-number --glob '*.py' '# TODO:' "${SEARCH_DIRS[@]}" > "${TMP_RG_OUT}" || echo "Warning: rg found no TODOs or failed. Exit code: $?"

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
        max_comment = length("TODO Comment");
        git_root_prefix = git_root proj_subdir; # Construct combined prefix
    }

    # Main block: Process each line from rg output
    {
        path = $1;
        # Remove the full prefix (handle potential missing slash at end if needed)
        sub(git_root_prefix, "", path);

        line_num = $2; # Use a different variable name than array name

        comment_text = substr($0, index($0, "# TODO:") + length("# TODO:"));
        sub(/^[ \t]+/, "", comment_text); # Remove leading space from comment

        # Store data in arrays (index starts from 1 by default with NR)
        paths[NR] = path;
        lines[NR] = line_num;
        comments[NR] = comment_text;

        # Update max widths based on content
        if (length(path) > max_path) max_path = length(path);
        if (length(line_num) > max_line) max_line = length(line_num);
        if (length(comment_text) > max_comment) max_comment = length(comment_text);
    }

    # END block: Print formatted table after reading all input
    END {
        # Add minimum padding spaces to max widths for aesthetics
        padding = 1
        max_path += padding;
        max_line += padding;
        # max_comment is used for calculation but not for padding the final column
        # max_comment += padding; # No longer needed here

        # Print Header (Left-aligned text: %-*s for first N-1, %s for last)
        printf "%-*s | %-*s | %s\n",
               max_path, "Source",
               max_line, "Line",
               "TODO Comment"; # Last column header is not padded

        # Print Separator line using calculated widths
        sep_path = sprintf("%-*s", max_path, ""); gsub(/ /, "-", sep_path);
        sep_line = sprintf("%-*s", max_line, ""); gsub(/ /, "-", sep_line);
        # Separator for last column should match its header length
        sep_comment = sprintf("%-*s", max_comment, ""); gsub(/ /, "-", sep_comment);
        printf "%s-|-%s-|-%s\n", sep_path, sep_line, sep_comment;

        # Print Data Rows (Left-aligned text: %-*s for first N-1, %s for last)
        for (i = 1; i <= NR; i++) {
            printf "%-*s | %-*s | %s\n",
                   max_path, paths[i],
                   max_line, lines[i],
                   comments[i]; # Last column data is not padded
        }
    }
    ' "${TMP_RG_OUT}" >> "${OUTPUT_FILE}" || echo "awk command failed! Exit code: $?"
# else
    # echo "DEBUG: Temp file ${TMP_RG_OUT} is empty or non-existent, skipping awk."
    # If no TODOs, maybe print a placeholder table or message?
    # For now, just print the headers if the file was empty
    if [ ! -s "${TMP_RG_OUT}" ]; then
        echo "Source | Line | TODO Comment" >> "${OUTPUT_FILE}"
        echo "-------|------|--------------" >> "${OUTPUT_FILE}"
        echo "(No TODOs found)" >> "${OUTPUT_FILE}"
    fi
fi
# echo "DEBUG: awk processing finished."

# Step 3: Clean up temp file
rm -f "${TMP_RG_OUT}"
# echo "DEBUG: Cleaned up temp file."

echo "" >> "${OUTPUT_FILE}"
echo "NOTE: This file is auto-generated by scripts/generate_code_todos.sh. Do not edit directly." >> "${OUTPUT_FILE}"

echo "Generated ${OUTPUT_FILE}" # Final script output for hook runner