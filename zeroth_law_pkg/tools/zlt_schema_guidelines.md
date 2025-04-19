# ZLT Tool Definition JSON Schema Guidelines

This document guides the AI in parsing the ground-truth `.txt` help output of a command-line tool and converting it into the structured high-trust `.json` format used by the Zeroth Law Toolkit (ZLT).

**Goal:** To accurately represent the tool's interface (options, arguments, subcommands, description) in a consistent JSON format.

**Core Principle:** You MUST interpret the specific help text provided in the `.txt` file directly. Do NOT attempt to write or use a generic parser programmatically. Use these guidelines and your understanding of common CLI help formats.

## Top-Level JSON Structure

The root of the JSON object should represent a single command or subcommand. It should contain the following keys:

```json
{
  "command_sequence": ["list", "of", "command", "parts"], // e.g., ["ruff"], ["ruff", "check"]
  "description": "A concise summary of what the command does.",
  "usage": "Optional: A string showing the typical invocation format (e.g., 'ruff [options] <subcommand>'). Extract if clearly present.",
  "options": [ /* Array of option objects */ ],
  "arguments": [ /* Array of argument objects */ ],
  "subcommands": [ /* Array of subcommand summary objects, if applicable */ ],
  "metadata": {
    "ground_truth_crc": "0xabcdef12" // Hex CRC32 of the source .txt file
  }
}
```

## Key Details & Parsing Hints

### 1. `command_sequence` (Required)
   - This should be an array of strings representing the command path being defined.
   - For `ruff --help`, it's `["ruff"]`.
   - For `ruff check --help`, it's `["ruff", "check"]`.

### 2. `description` (Required)
   - Usually found near the top of the help output, often as the first paragraph(s) before usage or options sections.
   - Capture the primary purpose of the command/subcommand. Concatenate multi-line descriptions into a single string with newline characters (`\n`) preserved.
   - **Sanitization:** If the description contains characters that have special meaning in JSON strings (like `\`), sanitize them appropriately (e.g., remove them if they are part of an example and not essential, or replace `\` with `\\` if the literal backslash is necessary). **Avoid** adding unnecessary escape characters that were not present or intended in the original help text.

### 3. `usage` (Optional)
   - Look for lines explicitly starting with "Usage:" or similar.
   - Capture the usage pattern shown. If multiple are shown, capture the most common or representative one.

### 4. `options` (Required, array)
   - Look for sections typically titled "Options:", "Flags:", etc.
   - Identify lines starting with `-` (short form) or `--` (long form).
   - Each option should be an object in the array:
     ```json
     {
       "short_form": "-f", // Optional: null if only long form exists
       "long_form": "--force", // Optional: null if only short form exists
       "argument": "<file>", // Optional: The name/type of the argument the option takes (e.g., <PATH>, <LEVEL>, VALUE). Null if it's just a flag.
       "description": "Description of what the option does.",
       "hidden": false // Optional: Set to true if marked as hidden/internal/deprecated
     }
     ```
   - Try to link short and long forms if they appear together (e.g., `-o, --output <file>`).
   - Capture the argument placeholder (`<file>`, `<level>`, etc.) if shown.
   - The text following the option name(s) is usually the `description`. Handle multi-line descriptions.

### 5. `arguments` (Required, array)
   - Look for sections titled "Arguments:", "Positional Arguments:", or identify them from the `Usage:` string if not explicitly listed.
   - These are typically required inputs that don't start with `-` or `--`.
   - Each argument should be an object:
     ```json
     {
       "name": "<input_file>", // The name/placeholder for the argument
       "description": "Description of the argument.",
       "required": true // Usually true for positional arguments, unless noted otherwise
     }
     ```

### 6. `subcommands` (Optional, array)
   - Look for sections titled "Commands:", "Subcommands:", etc.
   - If present, list the available subcommands mentioned.
   - Each subcommand should be a summary object:
     ```json
     {
       "name": "check", // The name of the subcommand
       "description": "Brief description of the subcommand."
     }
     ```
   - **Important:** This section only lists the *existence* of subcommands mentioned in the *parent's* help text. The full definition for the subcommand (e.g., `ruff check`) will be in its *own* separate JSON file derived from `ruff check --help`.

### 7. `metadata` (Required)
   - This object contains metadata about the definition file itself.
   - `ground_truth_crc` (Required): This field is critical for consistency checks. You MUST calculate the CRC32 checksum of the entire source `.txt` file's content (as a UTF-8 byte string) and store it here as a hexadecimal string (e.g., `"0x1a2b3c4d"`). You can use Python's `zlib.crc32` and `hex()` for this.

## General Guidelines

*   **Faithfulness:** Represent the information presented in the help text as accurately as possible. Do not invent options or arguments.
*   **Structure:** Adhere strictly to the JSON structure outlined above.
*   **Whitespace:** Normalize whitespace within descriptions, but preserve meaningful line breaks using `\\n`.
*   **Completeness:** Try to capture all presented options, arguments, and subcommands. If sections are ambiguous, make a best guess and potentially add a note in a development comment if needed (though comments are not part of the final JSON).
*   **Consistency:** Apply these rules consistently across all tool definitions.

## AI Update Consistency Constraint

When the AI (me) is tasked with updating an existing `.json` definition file due to changes detected in the ground-truth `.txt` file (signaled by a CRC mismatch), **maintaining consistency is paramount** for elements that have *not* fundamentally changed.

*   **Preserve Identifiers:** If an option or argument still exists and serves the same basic purpose, its internal JSON structure (including key names like `short_form`, `long_form`, `argument`, `name`) **must remain unchanged** unless the help text explicitly shows a renaming or structural change (e.g., `--old-name` becomes `--new-name`, or a flag now takes an argument).
*   **Reflect Only Actual Changes:** Updates to the `.json` file should accurately mirror the additions, removals, or modifications present in the new `.txt` help text. Do not invent changes or arbitrarily restructure existing entries.
*   **Focus:** The goal is to ensure that ZLT components relying on these `.json` definitions for programmatic access do not break due to unnecessary or inaccurate changes during the AI update process.

*(This document is a work in progress and may be updated as more tools are integrated.)*
