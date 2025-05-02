"""Path generation helpers for tool definitions."""

from pathlib import Path

# Placeholder - This should ideally use a context-aware way to get TOOLS_DIR
# For now, assume it's passed or configured.
# TOOLS_DIR = Path("src/zeroth_law/tools") # Remove hardcoded default


def _get_tool_def_path(tool_id: str, tools_dir: Path) -> Path:
    """Constructs the path to a tool definition JSON file."""
    # Basic assumption: tool_id might be <toolname> or <toolname>_<subcommand>
    tool_name = tool_id.split("_")[0]
    return tools_dir / tool_name / f"{tool_id}.json"
