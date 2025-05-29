#!/usr/bin/env bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "[Zeroth Law Hook] Running enhanced multi-project pre-commit hook..."

GIT_ROOT=$(git rev-parse --show-toplevel)
if [ -z "$GIT_ROOT" ]; then
    echo "[Zeroth Law Hook] Error: Could not determine Git repository root." >&2
    exit 1
fi

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM HEAD)
if [ -z "$STAGED_FILES" ]; then
    echo "[Zeroth Law Hook] No staged files to check."
    exit 0
fi

readarray -t STAGED_FILES_ARRAY <<<"$STAGED_FILES"
declare -A project_configs_to_run # Key: path to .pre-commit-config.yaml, Value: list of files

# Determine which pre-commit configs are relevant for the staged files
for file_abs_path_git_root in "${STAGED_FILES_ARRAY[@]}"; do
    file_full_path="$GIT_ROOT/$file_abs_path_git_root"
    current_dir=$(dirname "$file_full_path")
    config_found_for_file=""

    # Traverse upwards from the file's directory
    search_dir="$current_dir"
    while [[ "$search_dir" != "/" && "$search_dir" != "." && "$search_dir" != "$GIT_ROOT/.." && "$search_dir" =~ ^"$GIT_ROOT" ]]; do
        if [ -f "$search_dir/.pre-commit-config.yaml" ]; then
            config_found_for_file="$search_dir/.pre-commit-config.yaml"
            break # Found the closest config, stop searching this file
        fi
        # Stop if we are exactly at GIT_ROOT (don't go above)
        if [[ "$search_dir" == "$GIT_ROOT" ]]; then
             break
        fi
        search_dir=$(dirname "$search_dir")
    done

    # If traversal finished *without* finding a config file closer than root,
    # check if the root itself has one.
    if [[ -z "$config_found_for_file" && -f "$GIT_ROOT/.pre-commit-config.yaml" ]]; then
        # Only assign root config if the file is *directly* in the root OR no closer config was found
        # Check if the file's directory is the GIT_ROOT
        if [[ "$current_dir" == "$GIT_ROOT" ]]; then
             config_found_for_file="$GIT_ROOT/.pre-commit-config.yaml"
        else 
             # File is in a subdir, but no config found in its hierarchy, check root as last resort
             # This case implicitly means config_found_for_file is still empty here
             config_found_for_file="$GIT_ROOT/.pre-commit-config.yaml"
        fi
    fi

    # Assign the file to the found config (if any)
    if [ -n "$config_found_for_file" ]; then
        # Use Bash 4.0+ associative array feature check (-v)
        if [[ -v project_configs_to_run["$config_found_for_file"] ]]; then
           project_configs_to_run["$config_found_for_file"]+="$file_full_path "
        else
           project_configs_to_run["$config_found_for_file"]="$file_full_path "
        fi
    else
        echo "[Zeroth Law Hook] Info: File '$file_abs_path_git_root' is not covered by any .pre-commit-config.yaml."
    fi
done

if [ ${#project_configs_to_run[@]} -eq 0 ]; then
    echo "[Zeroth Law Hook] No .pre-commit-config.yaml configurations cover the staged files. Skipping checks."
    exit 0
fi

# --- Execute pre-commit for each relevant config ---
exit_code=0
for config_file_path in "${!project_configs_to_run[@]}"; do
    config_dir=$(dirname "$config_file_path")
    # Trim trailing space from file list string before converting to array
    files_for_this_config_str=$(echo "${project_configs_to_run[$config_file_path]}" | sed 's/ *$//')
    
    # Convert space-separated string of files to an array for pre-commit
    read -r -a files_array <<< "$files_for_this_config_str"

    echo "[Zeroth Law Hook] Processing config: $config_file_path"
    echo "[Zeroth Law Hook] Directory: $config_dir"
    # echo "[Zeroth Law Hook] Files: ${files_array[@]}" # Can be verbose

    # Change directory safely
    if ! pushd "$config_dir" > /dev/null; then
        echo "[Zeroth Law Hook] Error: Could not cd to $config_dir" >&2
        exit_code=1
        continue # Try next config if possible
    fi

    run_failed=false
    if [ -f "./pyproject.toml" ]; then
        echo "[Zeroth Law Hook] Python project detected (pyproject.toml found). Using 'uv run pre-commit ...'"
        if command -v uv >/dev/null 2>&1; then
            # Run uv with error handling
            # Pass files correctly quoted for the shell
            if ! uv run -- pre-commit run --config ./.pre-commit-config.yaml --files "${files_array[@]}"; then
                echo "[Zeroth Law Hook] 'uv run pre-commit' failed for $config_file_path." >&2
                run_failed=true
            fi
        else
            echo "[Zeroth Law Hook] Warning: 'uv' command not found, but pyproject.toml exists in $config_dir." >&2
            echo "Attempting to run 'pre-commit' directly for $config_file_path..." >&2
            if command -v pre-commit >/dev/null 2>&1; then
                 # Pass files correctly quoted for the shell
                if ! pre-commit run --config ./.pre-commit-config.yaml --files "${files_array[@]}"; then
                     echo "[Zeroth Law Hook] 'pre-commit' (direct) failed for $config_file_path." >&2
                     run_failed=true
                fi
            else
                echo "[Zeroth Law Hook] Error: 'pre-commit' command not found directly in $config_dir for Python project. Cannot run checks." >&2
                run_failed=true # ZLF projects require checks
            fi
        fi
    else
        echo "[Zeroth Law Hook] Not a Python project (no pyproject.toml in $config_dir)."
        echo "Attempting to run 'pre-commit' directly for $config_file_path..."
        if command -v pre-commit >/dev/null 2>&1; then
            # Pass files correctly quoted for the shell
            if ! pre-commit run --config ./.pre-commit-config.yaml --files "${files_array[@]}"; then
                 echo "[Zeroth Law Hook] 'pre-commit' (direct) failed for $config_file_path." >&2
                 run_failed=true
            fi
        else
            echo "[Zeroth Law Hook] Warning: 'pre-commit' command not found directly, and not a Python project in $config_dir." >&2
            echo "Skipping pre-commit checks for $config_file_path. To enable, install 'pre-commit' globally or make it a Python project." >&2
            # Do NOT set run_failed=true here; allow commit if pre-commit is not available for a non-Python project's config
        fi
    fi
    
    popd > /dev/null # Go back to original directory
    
    if $run_failed; then
        exit_code=1 # Record failure but continue processing other configs if needed
    else
         echo "[Zeroth Law Hook] Checks completed successfully for config: $config_file_path"
    fi
done

if [ $exit_code -eq 0 ]; then
    echo "[Zeroth Law Hook] All relevant pre-commit checks passed."
fi

exit $exit_code 