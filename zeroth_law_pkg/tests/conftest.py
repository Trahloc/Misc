import shlex
import subprocess

import pytest


def _run_tool_help_internal(command_list):  # Renamed internal helper
    """Runs a command list with --help and captures output."""
    # ... (rest of the implementation is the same)
    try:
        process = subprocess.run(
            ["poetry", "run"] + command_list + ["--help"],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
        )
        return process.stdout
    except FileNotFoundError:
        pytest.fail(f"Tool command not found: {shlex.join(command_list)}")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Tool command ' {shlex.join(command_list + ['--help'])}' failed with exit code {e.returncode}:\n{e.stderr}")
    except Exception as e:
        pytest.fail(f"Unexpected error running tool help command: {e}")


@pytest.fixture
def run_tool_help_func():  # Fixture that returns the helper function
    """Pytest fixture that provides the tool help execution function."""
    return _run_tool_help_internal


# --- NEW Simplified Text Processing ---
def simplify_text_for_matching(text):
    """Prepares text for basic substring matching.

    Keeps only alphanumeric and spaces, converts to lowercase,
    collapses whitespace, and strips leading/trailing spaces.
    """
    if not isinstance(text, str):
        return ""  # Handle non-string input gracefully
    # Keep only alphanumeric and spaces
    processed = "".join(c for c in text if c.isalnum() or c.isspace())
    # Lowercase
    processed = processed.lower()
    # Collapse whitespace and strip
    processed = " ".join(processed.split())
    return processed


@pytest.fixture
def text_simplifier_func():  # New fixture name
    """Pytest fixture providing the text simplification function."""
    return simplify_text_for_matching


# --- END NEW ---

# --- OLD Fuzzy Pattern (Commented out/Removed) ---
# def create_fuzzy_help_pattern(help_text):
#     r"""Converts a help string into a regex pattern.
#
#     Keeps alphanumeric literally.
#     Escapes safe punctuation.
#     Replaces regex metacharacters with '.'.
#     Collapses whitespace sequences to r'\\s+'.
#     Ignores specific characters (like ':').
#     """
#     regex_metachars = r\".^$*+?{}[]\\|()\"  # Characters to replace with .
#     chars_to_ignore = \":\"  # Characters to skip entirely
#     pattern = \"\"
#     in_whitespace = False
#
#     # Strip trailing whitespace from input to avoid spurious \\s+ at the end
#     help_text = help_text.rstrip()
#
#     for char in help_text:
#         if char in chars_to_ignore:
#             # Ensure preceding whitespace is added before skipping
#             if in_whitespace:
#                 pattern += r\"\\s+\"
#                 in_whitespace = False
#             continue  # Skip this character
#         elif char.isalnum():
#             if in_whitespace:
#                 pattern += r\"\\s+\"
#                 in_whitespace = False
#             pattern += char  # Keep alnum literally
#         elif char.isspace():
#             if not in_whitespace:
#                 in_whitespace = True  # Start whitespace sequence
#         elif char in regex_metachars:
#             if in_whitespace:
#                 pattern += r\"\\s+\"
#                 in_whitespace = False
#             pattern += \".\"  # Replace meta char with wildcard
#         else:
#             # Other punctuation/symbols: escape and add
#             if in_whitespace:
#                 pattern += r\"\\s+\"
#                 in_whitespace = False
#             pattern += re.escape(char)
#
#     # Add trailing whitespace if needed
#     # REMOVED: This might add unwanted whitespace, especially with rstrip()
#     # if in_whitespace:
#     #     pattern += r\"\\s+\"
#
#     return pattern
#
# @pytest.fixture
# def fuzzy_pattern_func():
#     """Pytest fixture that provides the fuzzy help pattern creation function."""
#     return create_fuzzy_help_pattern
# --- END OLD ---
