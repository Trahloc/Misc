import click
import structlog
import json
from pathlib import Path

log = structlog.get_logger()

# --- Define Paths (relative to this file's assumed location) ---
# This might need adjustment if the script execution context changes
try:
    _SCRIPT_DIR = Path(__file__).parent.resolve()
    # Go up from subcommands/definition/ -> subcommands/ -> src/zeroth_law/ -> src/ -> workspace root
    # Adjust based on actual structure if needed
    # Assuming WORKSPACE_ROOT is determined correctly elsewhere (e.g., cli.py context)
    # For now, let's assume these are passed or globally available constants/functions
    # that get patched in tests.
    # Define placeholder constants that tests will patch
    WORKSPACE_ROOT = Path(".")  # Placeholder, tests must patch
    TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"  # Placeholder
    ZLT_CAPABILITIES_PATH = WORKSPACE_ROOT / "src" / "zeroth_law" / "zlt_capabilities.json"  # Placeholder
    ZLT_OPTIONS_DEFINITIONS_PATH = WORKSPACE_ROOT / "src" / "zeroth_law" / "zlt_options_definitions.json"  # Placeholder

except NameError:
    # Fallback if __file__ is not defined (e.g., interactive execution?)
    log.warning("Could not determine script directory via __file__.")
    WORKSPACE_ROOT = Path(".")
    TOOLS_DIR = WORKSPACE_ROOT / "src" / "zeroth_law" / "tools"
    ZLT_CAPABILITIES_PATH = WORKSPACE_ROOT / "src" / "zeroth_law" / "zlt_capabilities.json"
    ZLT_OPTIONS_DEFINITIONS_PATH = WORKSPACE_ROOT / "src" / "zeroth_law" / "zlt_options_definitions.json"


# --- Helper Functions (Consider moving to a common utils module) ---
def get_tool_def_path(tool_id: str) -> Path:
    """Constructs the path to a tool definition JSON file."""
    # Basic assumption: tool_id might be <toolname> or <toolname>_<subcommand>
    tool_name = tool_id.split("_")[0]
    return TOOLS_DIR / tool_name / f"{tool_id}.json"


def load_json_file(path: Path) -> dict | None:
    """Loads JSON data from a file, handling errors."""
    if not path.is_file():
        log.error(f"File not found: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON from {path}: {e}")
        return None
    except OSError as e:
        log.error(f"Error reading file {path}: {e}")
        return None
    except Exception as e:
        log.exception(f"Unexpected error loading JSON from {path}: {e}")
        return None


def write_json_file(path: Path, data: dict) -> bool:
    """Writes data to a JSON file with standard formatting."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        return True
    except OSError as e:
        log.error(f"Error writing JSON to {path}: {e}")
        return False
    except Exception as e:
        log.exception(f"Unexpected error writing JSON to {path}: {e}")
        return False


# --- Command Implementations ---

# CONTEXT_SETTINGS_DEFINITION = {"ignore_unknown_options": True, "allow_interspersed_args": False}


@click.group("definition")  # Removed context settings from here
def definition_group():
    """Commands for managing tool definition JSON files."""
    pass


@definition_group.command("add-capability")
@click.argument("tool_id")
@click.argument("capability_name")
def add_capability(tool_id: str, capability_name: str):
    """Adds a capability to a tool definition's metadata."""
    log = structlog.get_logger(command="add-capability")  # Add command context
    log.info("Attempting to add capability...", tool=tool_id, capability=capability_name)

    # 1. Load capabilities definition for validation
    valid_capabilities = load_json_file(ZLT_CAPABILITIES_PATH)
    if valid_capabilities is None:
        click.echo(f"Error: Could not load capability definitions from {ZLT_CAPABILITIES_PATH}", err=True)
        raise click.Abort()
    if capability_name not in valid_capabilities:
        click.echo(
            f"Error: Capability '{capability_name}' is not a valid capability defined in {ZLT_CAPABILITIES_PATH}.",
            err=True,
        )
        click.echo(f"Valid capabilities are: {', '.join(valid_capabilities.keys())}")
        raise click.Abort()

    # 2. Load target tool definition
    tool_json_path = get_tool_def_path(tool_id)
    tool_data = load_json_file(tool_json_path)
    if tool_data is None:
        click.echo(f"Error: Could not load tool definition for '{tool_id}' from {tool_json_path}", err=True)
        raise click.Abort()

    # 3. Modify data structure
    metadata = tool_data.setdefault("metadata", {})
    capabilities_list = metadata.setdefault("provides_capabilities", [])

    if not isinstance(capabilities_list, list):
        click.echo(f"Error: 'metadata.provides_capabilities' in {tool_json_path} is not a list.", err=True)
        raise click.Abort()

    if capability_name in capabilities_list:
        click.echo(f"Info: Capability '{capability_name}' already exists for tool '{tool_id}'. No changes made.")
        return  # Idempotent success

    capabilities_list.append(capability_name)
    # Sort for consistency, although order isn't strictly significant
    capabilities_list.sort()

    # 4. Write updated data back
    if write_json_file(tool_json_path, tool_data):
        click.echo(f"Successfully added capability '{capability_name}' to tool '{tool_id}' definition.")
        log.info("Capability added successfully.", tool=tool_id, capability=capability_name)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error("Failed to write updated definition.", tool=tool_id, path=str(tool_json_path))
        raise click.Abort()


@definition_group.command("remove-capability")
@click.argument("tool_id")
@click.argument("capability_name")
def remove_capability(tool_id: str, capability_name: str):
    """Removes a capability from a tool definition's metadata."""
    log = structlog.get_logger(command="remove-capability")
    log.info("Attempting to remove capability...", tool=tool_id, capability=capability_name)

    # No need to validate against capabilities file for removal

    # 1. Load target tool definition
    tool_json_path = get_tool_def_path(tool_id)
    tool_data = load_json_file(tool_json_path)
    if tool_data is None:
        click.echo(f"Error: Could not load tool definition for '{tool_id}' from {tool_json_path}", err=True)
        raise click.Abort()

    # 2. Modify data structure
    metadata = tool_data.get("metadata")
    if not metadata or not isinstance(metadata, dict):
        click.echo(
            f"Error: 'metadata' object missing or invalid in {tool_json_path}. Cannot remove capability.", err=True
        )
        raise click.Abort()

    capabilities_list = metadata.get("provides_capabilities")
    if not isinstance(capabilities_list, list):
        # If key exists but isn't a list, or if key doesn't exist, the capability isn't there anyway.
        click.echo(
            f"Info: Capability '{capability_name}' not found for tool '{tool_id}' (or capabilities list invalid/missing). No changes made."
        )
        return  # Idempotent success

    if capability_name not in capabilities_list:
        click.echo(f"Info: Capability '{capability_name}' not found for tool '{tool_id}'. No changes made.")
        return  # Idempotent success

    capabilities_list.remove(capability_name)
    # Sort for consistency
    capabilities_list.sort()

    # 3. Write updated data back
    if write_json_file(tool_json_path, tool_data):
        click.echo(f"Successfully removed capability '{capability_name}' from tool '{tool_id}' definition.")
        log.info("Capability removed successfully.", tool=tool_id, capability=capability_name)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error("Failed to write updated definition.", tool=tool_id, path=str(tool_json_path))
        raise click.Abort()


@definition_group.command("set-filetypes")
@click.argument("tool_id")
@click.argument("extensions", nargs=-1)  # Accepts one or more extensions
def set_filetypes(tool_id: str, extensions: tuple[str]):
    """Sets (overwrites) the supported filetypes for a tool definition."""
    log = structlog.get_logger(command="set-filetypes")
    log.info("Attempting to set filetypes...", tool=tool_id, filetypes=list(extensions))

    if not extensions:
        click.echo("Error: At least one file extension (e.g., '.py' or '*') must be provided.", err=True)
        raise click.Abort()

    # Basic validation: ensure extensions start with a dot or are "*"
    validated_extensions = []
    for ext in extensions:
        if ext == "*":
            validated_extensions.append("*")
        elif ext.startswith(".") and len(ext) > 1:
            validated_extensions.append(ext.lower())  # Store lowercase
        else:
            click.echo(
                f"Error: Invalid file extension format '{ext}'. Must start with '.' (e.g., '.py') or be '*'", err=True
            )
            raise click.Abort()

    # Remove duplicates and sort
    unique_sorted_extensions = sorted(list(set(validated_extensions)))

    # 1. Load target tool definition
    tool_json_path = get_tool_def_path(tool_id)
    tool_data = load_json_file(tool_json_path)
    if tool_data is None:
        click.echo(f"Error: Could not load tool definition for '{tool_id}' from {tool_json_path}", err=True)
        raise click.Abort()

    # 2. Modify data structure (overwrite existing)
    metadata = tool_data.setdefault("metadata", {})
    metadata["supported_filetypes"] = unique_sorted_extensions

    # 3. Write updated data back
    if write_json_file(tool_json_path, tool_data):
        click.echo(f"Successfully set filetypes for tool '{tool_id}' definition to: {unique_sorted_extensions}")
        log.info("Filetypes set successfully.", tool=tool_id, filetypes=unique_sorted_extensions)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error("Failed to write updated definition.", tool=tool_id, path=str(tool_json_path))
        raise click.Abort()


@definition_group.command("map-option")
@click.argument("tool_id")
@click.argument("tool_option_name")
@click.argument("zlt_option_name")
def map_option(tool_id: str, tool_option_name: str, zlt_option_name: str):
    """Maps a tool's option/argument TOOL_OPTION_NAME to a canonical ZLT option ZLT_OPTION_NAME for tool TOOL_ID."""
    log = structlog.get_logger(command="map-option")
    log.info("Attempting to map option...", tool=tool_id, tool_option=tool_option_name, zlt_option=zlt_option_name)

    # 1. Load ZLT options definition for validation
    valid_zlt_options = load_json_file(ZLT_OPTIONS_DEFINITIONS_PATH)
    if valid_zlt_options is None:
        click.echo(f"Error: Could not load ZLT option definitions from {ZLT_OPTIONS_DEFINITIONS_PATH}", err=True)
        raise click.Abort()
    if zlt_option_name not in valid_zlt_options:
        click.echo(f"Error: ZLT option '{zlt_option_name}' is not defined in {ZLT_OPTIONS_DEFINITIONS_PATH}.", err=True)
        click.echo(f"Valid options are: {', '.join(valid_zlt_options.keys())}")
        raise click.Abort()

    # 2. Load target tool definition
    tool_json_path = get_tool_def_path(tool_id)
    tool_data = load_json_file(tool_json_path)
    if tool_data is None:
        click.echo(f"Error: Could not load tool definition for '{tool_id}' from {tool_json_path}", err=True)
        raise click.Abort()

    # 3. Find and modify the specific tool option/argument
    found_and_modified = False
    # Check in options list
    options_list = tool_data.setdefault("options", [])
    if isinstance(options_list, list):
        for option_obj in options_list:
            if isinstance(option_obj, dict) and option_obj.get("name") == tool_option_name:
                option_obj["maps_to_zlt_option"] = zlt_option_name
                found_and_modified = True
                break  # Found and modified in options
    else:
        click.echo(f"Warning: 'options' key in {tool_json_path} is not a list. Cannot map option.", err=True)

    # If not found in options, check in arguments list
    if not found_and_modified:
        arguments_list = tool_data.setdefault("arguments", [])
        if isinstance(arguments_list, list):
            for arg_obj in arguments_list:
                if isinstance(arg_obj, dict) and arg_obj.get("name") == tool_option_name:
                    arg_obj["maps_to_zlt_option"] = zlt_option_name
                    found_and_modified = True
                    break  # Found and modified in arguments
        else:
            click.echo(f"Warning: 'arguments' key in {tool_json_path} is not a list. Cannot map argument.", err=True)

    if not found_and_modified:
        click.echo(
            f"Error: Tool option/argument '{tool_option_name}' not found in definition for '{tool_id}'.", err=True
        )
        raise click.Abort()

    # 4. Write updated data back
    if write_json_file(tool_json_path, tool_data):
        click.echo(
            f"Successfully mapped tool option '{tool_option_name}' to ZLT option '{zlt_option_name}' for tool '{tool_id}'."
        )
        log.info("Option mapped successfully.", tool=tool_id, tool_option=tool_option_name, zlt_option=zlt_option_name)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error("Failed to write updated definition.", tool=tool_id, path=str(tool_json_path))
        raise click.Abort()


@definition_group.command("unmap-option")
@click.argument("tool_id")
@click.argument("tool_option_name")
def unmap_option(tool_id: str, tool_option_name: str):
    """Removes the ZLT option mapping from TOOL_OPTION_NAME for tool TOOL_ID."""
    log = structlog.get_logger(command="unmap-option")
    log.info("Attempting to unmap option...", tool=tool_id, tool_option=tool_option_name)

    # No need to validate against options definitions for removal

    # 1. Load target tool definition
    tool_json_path = get_tool_def_path(tool_id)
    tool_data = load_json_file(tool_json_path)
    if tool_data is None:
        click.echo(f"Error: Could not load tool definition for '{tool_id}' from {tool_json_path}", err=True)
        raise click.Abort()

    # 2. Find and modify the specific tool option/argument
    modified = False
    # Check in options list
    options_list = tool_data.get("options", [])  # Use get, don't setdefault if missing
    if isinstance(options_list, list):
        for option_obj in options_list:
            if isinstance(option_obj, dict) and option_obj.get("name") == tool_option_name:
                if "maps_to_zlt_option" in option_obj:
                    del option_obj["maps_to_zlt_option"]
                    modified = True
                    break  # Found and modified in options
    else:
        log.warning(f"'options' key in {tool_json_path} is not a list. Skipping options check for unmap.")

    # Check in arguments list (only if not already modified)
    if not modified:
        arguments_list = tool_data.get("arguments", [])  # Use get
        if isinstance(arguments_list, list):
            for arg_obj in arguments_list:
                if isinstance(arg_obj, dict) and arg_obj.get("name") == tool_option_name:
                    if "maps_to_zlt_option" in arg_obj:
                        del arg_obj["maps_to_zlt_option"]
                        modified = True
                        break  # Found and modified in arguments
        else:
            log.warning(f"'arguments' key in {tool_json_path} is not a list. Skipping arguments check for unmap.")

    if not modified:
        click.echo(
            f"Info: Tool option/argument '{tool_option_name}' not found or already unmapped for tool '{tool_id}'. No changes made."
        )
        return  # Idempotent success

    # 3. Write updated data back
    if write_json_file(tool_json_path, tool_data):
        click.echo(f"Successfully unmapped tool option '{tool_option_name}' for tool '{tool_id}'.")
        log.info("Option unmapped successfully.", tool=tool_id, tool_option=tool_option_name)
    else:
        click.echo(f"Error: Failed to write updated definition to {tool_json_path}", err=True)
        log.error("Failed to write updated definition.", tool=tool_id, path=str(tool_json_path))
        raise click.Abort()
