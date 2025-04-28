### `metadata` Object

The `metadata` object provides high-level information about the tool definition.

*   `tool_name` (string, required): The canonical name of the tool (e.g., "ruff", "pytest").
*   `command_name` (string or null, required): The specific subcommand being defined, or `null` if it's the base command.
*   `description` (string, required): A brief description of what this specific command/subcommand does.
*   `ground_truth_crc` (string, required): The CRC32 hex string calculated from the tool's `--help` output (`command --help | cat`). **Managed exclusively by automated tooling; DO NOT EDIT MANUALLY.** Starts as `"0x00000000"` for skeleton files.
*   `schema_version` (string, required): The version of this schema the file adheres to (e.g., "1.0").
*   `provides_capabilities` (array of strings, required): A list of canonical capability names (keys from `zlt_capabilities.json`) that this specific tool command fulfills (e.g., `["Linter", "Formatter"]`).
*   `supported_filetypes` (array of strings, required): A list of file extensions (including the dot, e.g., `".py"`, `".toml"`) that this tool command can process. Use `["*"]` if the tool is filetype-agnostic.

#### Option/Argument Object Structure

Each key within the `options` and `arguments` objects represents a specific option or argument name (e.g., `"--verbose"`, `"target_directory"`). The value associated with each key is an object describing that option/argument:

*   `type` (string, required): The type of the option/argument. Must be one of:
    *   `"flag"`: A boolean switch (e.g., `--verbose`).
    *   `"value"`: An option that takes a value (e.g., `--config FILE`).
    *   `"positional"`: A positional argument.
*   `description` (string, required): The help text describing the option/argument, as obtained from the tool's help output.
*   `value_name` (string or null, optional): For `type: "value"`, the placeholder name for the value shown in help text (e.g., `"FILE"` for `--config FILE`). Defaults to `null`.
*   `nargs` (string or integer or null, optional): For `type: "positional"` or `type: "value"`, specifies the number of arguments consumed. Uses standard conventions (`"?"`=0..1, `"*"`=0..N, `"+"`=1..N, integer=N). Defaults to `1` for `value` and `positional` if not specified.
*   `required` (boolean, optional): Indicates if the option/argument is mandatory. Defaults to `false`.
*   `default` (any type or null, optional): The default value if the option/argument is not provided. Defaults to `null`.
*   `choices` (array of strings or null, optional): A list of allowed values for the option/argument. Defaults to `null`.
*   `maps_to_zlt_option` (string or null, optional): The canonical ZLT option name (key from `zlt_options_definitions.json`) that this specific tool option/argument fulfills (e.g., `"verbose"`, `"paths"`). Defaults to `null` if it doesn't map directly to a universal ZLT concept.