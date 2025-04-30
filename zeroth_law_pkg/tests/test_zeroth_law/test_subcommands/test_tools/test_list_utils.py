"""Tests for src/zeroth_law/subcommands/tools/list_utils.py"""

import pytest
import tomlkit
from pathlib import Path
from typing import List, Dict, Set, Tuple, Any, Union

# Module under test
from zeroth_law.subcommands.tools.list_utils import (
    modify_tool_list,
    list_tool_list,
    # _format_nested_dict_to_list, # Import from common
    # _parse_to_nested_dict, # Import from common
    # ParsedHierarchy, # Import from common
    # NodeData # Import from common
)

# --- Import from shared utils --- #
from zeroth_law.common.hierarchical_utils import (
    NodeData,
    ParsedHierarchy,
    parse_to_nested_dict as _parse_to_nested_dict,
    format_nested_dict_to_list as _format_nested_dict_to_list,
)

# Need the old parser only for comparing its simple output format in one test
from zeroth_law.common.config_loader import _parse_hierarchical_list as _parse_simple_hierarchical_list

# --- Fixtures --- #


@pytest.fixture
def mock_pyproject_file(tmp_path: Path) -> Path:
    """Creates a temporary pyproject.toml file."""
    pyproject_path = tmp_path / "pyproject.toml"
    # Start with an empty structure
    initial_content = tomlkit.dumps({})
    pyproject_path.write_text(initial_content, encoding="utf-8")
    return pyproject_path


def write_config(path: Path, content: Dict[str, Any]):
    """Helper to write a specific dict to the temp pyproject.toml."""
    # Ensure base structure exists
    doc = tomlkit.parse(path.read_text())
    tool_table = doc.setdefault("tool", tomlkit.table())
    zt_table = tool_table.setdefault("zeroth-law", tomlkit.table())
    managed_table = zt_table.setdefault("managed-tools", tomlkit.table())

    # Add or overwrite whitelist/blacklist
    if "whitelist" in content:
        wl_array = tomlkit.array()
        wl_array.extend(content["whitelist"])
        wl_array.multiline(True)
        managed_table["whitelist"] = wl_array
    if "blacklist" in content:
        bl_array = tomlkit.array()
        bl_array.extend(content["blacklist"])
        bl_array.multiline(True)
        managed_table["blacklist"] = bl_array

    path.write_text(tomlkit.dumps(doc), encoding="utf-8")


# --- Test Cases --- #

# region Test Parsing and Formatting
# ==================================================

# Test cases for _parse_to_nested_dict
PARSE_TEST_CASES = [
    # Input List                        Expected Nested Dictionary
    ([], {}),  # Empty list
    (["tool_a"], {"tool_a": {"_explicit": True}}),  # Simple tool
    (["tool_a:*"], {"tool_a": {"_explicit": True, "_all": True}}),  # Tool with *
    (["tool_a:sub1"], {"tool_a": {"sub1": {"_explicit": True}}}),  # Tool with sub
    (
        ["tool_a:sub1,sub2"],
        {"tool_a": {"sub1": {"_explicit": True}, "sub2": {"_explicit": True}}},
    ),  # Tool with multiple subs
    (["tool_a:sub1:*"], {"tool_a": {"sub1": {"_explicit": True, "_all": True}}}),  # Sub with *
    (["tool_a:sub1:subsub1"], {"tool_a": {"sub1": {"subsub1": {"_explicit": True}}}}),  # Nested sub
    (
        ["tool_a:sub1:subsub1,subsub2"],
        {"tool_a": {"sub1": {"subsub1": {"_explicit": True}, "subsub2": {"_explicit": True}}}},
    ),  # Nested multiple subs
    (["tool_a", "tool_a:sub1"], {"tool_a": {"_explicit": True, "sub1": {"_explicit": True}}}),  # Explicit tool and sub
    (["tool_a:sub1", "tool_a"], {"tool_a": {"_explicit": True, "sub1": {"_explicit": True}}}),  # Order shouldn't matter
    (
        ["tool_a:*", "tool_a:sub1"],
        {"tool_a": {"_explicit": True, "_all": True}},
    ),  # Tool:* overrides specific sub later defined
    (
        ["tool_a:sub1", "tool_a:*"],
        {"tool_a": {"_explicit": True, "_all": True}},
    ),  # Specific sub overridden by later Tool:*
    (
        ["tool_a:sub1:*", "tool_a:sub1:subsub1"],
        {"tool_a": {"sub1": {"_explicit": True, "_all": True}}},
    ),  # Sub:* overrides deeper subsub
    (
        ["tool_a:sub1:subsub1", "tool_a:sub1:*"],
        {"tool_a": {"sub1": {"_explicit": True, "_all": True}}},
    ),  # Deeper subsub overridden by later Sub:*
    (
        ["tool_a:sub1", "tool_b", "tool_a:sub2"],
        {"tool_a": {"sub1": {"_explicit": True}, "sub2": {"_explicit": True}}, "tool_b": {"_explicit": True}},
    ),  # Mixed
    (["tool_a::sub1"], {}),  # Invalid empty component
    (["tool_a:,"], {"tool_a": {}}),  # Invalid empty sub after comma - should parse tool node only
    (["tool_a", ""], {"tool_a": {"_explicit": True}}),  # Empty string in list
    (["  tool_a : sub1  "], {"tool_a": {"sub1": {"_explicit": True}}}),  # Whitespace handling
    ([":*"], {}),  # Invalid :* alone
    (
        ["tool_a:sub1:", "tool_b"],
        {"tool_a": {"sub1": {"_explicit": True}}, "tool_b": {"_explicit": True}},
    ),  # Trailing colon ignored
]


@pytest.mark.parametrize("input_list, expected_dict", PARSE_TEST_CASES)
def test_parse_to_nested_dict(input_list: List[str], expected_dict: ParsedHierarchy):
    """Test the hierarchical string list parser."""
    assert _parse_to_nested_dict(input_list) == expected_dict


# Test cases for _format_nested_dict_to_list (reverse of parse tests)
# Note: Output is always sorted
FORMAT_TEST_CASES = [
    # Expected Output List                Input Nested Dictionary
    ([], {}),  # Empty
    (["tool_a"], {"tool_a": {"_explicit": True}}),
    (["tool_a:*"], {"tool_a": {"_explicit": True, "_all": True}}),
    (["tool_a:sub1"], {"tool_a": {"sub1": {"_explicit": True}}}),
    (
        ["tool_a:sub1", "tool_a:sub2"],
        {"tool_a": {"sub1": {"_explicit": True}, "sub2": {"_explicit": True}}},
    ),  # Note: comma format lost
    (["tool_a:sub1:*"], {"tool_a": {"sub1": {"_explicit": True, "_all": True}}}),
    (["tool_a:sub1:subsub1"], {"tool_a": {"sub1": {"subsub1": {"_explicit": True}}}}),
    (
        ["tool_a:sub1:subsub1", "tool_a:sub1:subsub2"],
        {"tool_a": {"sub1": {"subsub1": {"_explicit": True}, "subsub2": {"_explicit": True}}}},
    ),
    (["tool_a", "tool_a:sub1"], {"tool_a": {"_explicit": True, "sub1": {"_explicit": True}}}),
    (
        ["tool_a:*"],
        {"tool_a": {"_explicit": True, "_all": True, "sub1": {"_explicit": True}}},
    ),  # _all=True prunes deeper items on format
    (
        ["tool_a:sub1:*"],
        {"tool_a": {"sub1": {"_explicit": True, "_all": True, "subsub1": {"_explicit": True}}}},
    ),  # _all=True prunes deeper
    (
        ["tool_a:sub1", "tool_a:sub2", "tool_b"],
        {"tool_a": {"sub1": {"_explicit": True}, "sub2": {"_explicit": True}}, "tool_b": {"_explicit": True}},
    ),
    # Case where only intermediate node exists but isn't explicit
    ([], {"tool_a": {"sub1": {}}}),
    (["tool_a:sub1"], {"tool_a": {"sub1": {"_explicit": True}}}),
]


@pytest.mark.parametrize("expected_list, input_dict", FORMAT_TEST_CASES)
def test_format_nested_dict_to_list(expected_list: List[str], input_dict: ParsedHierarchy):
    """Test the nested dictionary formatter."""
    assert _format_nested_dict_to_list(input_dict) == expected_list


# endregion

# region Test modify_tool_list Add/Remove
# ==================================================

# Structure: (initial_wl, initial_bl, items_to_add, apply_all, force, expected_final_wl, expected_final_bl, expect_modified)
MODIFY_ADD_TEST_CASES = [
    # --- Basic Add --- #
    ([], [], ("tool_a",), False, False, ["tool_a"], [], True),  # Add simple
    (["tool_b"], [], ("tool_a",), False, False, ["tool_a", "tool_b"], [], True),  # Add to existing
    (["tool_a"], [], ("tool_a",), False, False, ["tool_a"], [], False),  # Add existing (no change)
    ([], [], ("tool_a:sub1",), False, False, ["tool_a:sub1"], [], True),  # Add sub
    (["tool_a:sub1"], [], ("tool_a:sub2",), False, False, ["tool_a:sub1", "tool_a:sub2"], [], True),  # Add another sub
    (["tool_a:sub1"], [], ("tool_a:sub1",), False, False, ["tool_a:sub1"], [], False),  # Add existing sub
    ([], [], ("tool_a:sub1:subsub1",), False, False, ["tool_a:sub1:subsub1"], [], True),  # Add nested sub
    # --- Add with --all / :* --- #
    ([], [], ("tool_a",), True, False, ["tool_a:*"], [], True),  # Add simple --all
    ([], [], ("tool_a:*",), False, False, ["tool_a:*"], [], True),  # Add simple with :*
    (["tool_a:sub1"], [], ("tool_a",), True, False, ["tool_a:*"], [], True),  # Add --all overrides existing sub
    (["tool_a:sub1"], [], ("tool_a:*",), False, False, ["tool_a:*"], [], True),  # Add :* overrides existing sub
    (["tool_a:*"], [], ("tool_a",), True, False, ["tool_a:*"], [], False),  # Add --all when :* exists (no change)
    (["tool_a:*"], [], ("tool_a:*",), False, False, ["tool_a:*"], [], False),  # Add :* when :* exists (no change)
    (["tool_a:*"], [], ("tool_a:sub1",), False, False, ["tool_a:*"], [], False),  # Add sub when :* exists (no change)
    ([], [], ("tool_a:sub1",), True, False, ["tool_a:sub1:*"], [], True),  # Add sub --all
    ([], [], ("tool_a:sub1:*",), False, False, ["tool_a:sub1:*"], [], True),  # Add sub with :*
    (
        ["tool_a:sub1:subsub1"],
        [],
        ("tool_a:sub1",),
        True,
        False,
        ["tool_a:sub1:*"],
        [],
        True,
    ),  # Add sub --all overrides subsub
    # --- Add with Conflicts (No Force) --- #
    ([], ["tool_a"], ("tool_a",), False, False, [], ["tool_a"], False),  # Conflict simple
    ([], ["tool_a:*"], ("tool_a",), False, False, [], ["tool_a:*"], False),  # Conflict simple vs :*
    ([], ["tool_a"], ("tool_a:*",), False, False, [], ["tool_a"], False),  # Conflict :* vs simple
    ([], ["tool_a:*"], ("tool_a:*",), False, False, [], ["tool_a:*"], False),  # Conflict :* vs :*
    ([], ["tool_a:sub1"], ("tool_a:sub1",), False, False, [], ["tool_a:sub1"], False),  # Conflict sub
    ([], ["tool_a:*"], ("tool_a:sub1",), False, False, [], ["tool_a:*"], False),  # Conflict sub vs parent:*
    ([], ["tool_a:sub1"], ("tool_a:*",), False, False, [], ["tool_a:sub1"], False),  # Conflict parent:* vs sub
    (
        [],
        ["tool_a:sub1:*"],
        ("tool_a:sub1:subsub1",),
        False,
        False,
        [],
        ["tool_a:sub1:*"],
        False,
    ),  # Conflict subsub vs sub:*
    ([], ["tool_a"], ("tool_a",), True, False, [], ["tool_a"], False),  # Conflict simple --all
    ([], ["tool_a:sub1"], ("tool_a",), True, False, [], ["tool_a:sub1"], False),  # Conflict parent --all vs sub
    # --- Add with Conflicts (Force) --- #
    ([], ["tool_a"], ("tool_a",), False, True, ["tool_a"], [], True),  # Force simple
    ([], ["tool_a:*"], ("tool_a",), False, True, ["tool_a"], [], True),  # Force simple vs :* (removes other :*)
    ([], ["tool_a"], ("tool_a:*",), False, True, ["tool_a:*"], [], True),  # Force :* vs simple (removes other simple)
    ([], ["tool_a:*"], ("tool_a:*",), False, True, ["tool_a:*"], [], True),  # Force :* vs :*
    ([], ["tool_a:sub1"], ("tool_a:sub1",), False, True, ["tool_a:sub1"], [], True),  # Force sub
    (
        [],
        ["tool_a:*"],
        ("tool_a:sub1",),
        False,
        True,
        ["tool_a:sub1"],
        [],
        True,
    ),  # Force sub vs parent:* (removes other parent:*)
    (
        [],
        ["tool_a:sub1"],
        ("tool_a:*",),
        False,
        True,
        ["tool_a:*"],
        [],
        True,
    ),  # Force parent:* vs sub (removes other sub)
    (
        [],
        ["tool_a:sub1:*"],
        ("tool_a:sub1:subsub1",),
        False,
        True,
        ["tool_a:sub1:subsub1"],
        [],
        True,
    ),  # Force subsub vs sub:* (removes other sub:*)
    ([], ["tool_a"], ("tool_a",), True, True, ["tool_a:*"], [], True),  # Force simple --all
    (
        [],
        ["tool_a:sub1"],
        ("tool_a",),
        True,
        True,
        ["tool_a:*"],
        [],
        True,
    ),  # Force parent --all vs sub (removes other sub)
    (
        [],
        ["tool_a:*"],
        ("tool_a",),
        True,
        True,
        ["tool_a:*"],
        [],
        True,
    ),  # Force parent --all vs parent:* (removes other parent:*)
]


@pytest.mark.parametrize(
    "initial_wl, initial_bl, items_to_add, apply_all, force, expected_final_wl, expected_final_bl, expect_modified",
    MODIFY_ADD_TEST_CASES,
)
def test_modify_add_whitelist(
    mock_pyproject_file: Path,
    initial_wl: List[str],
    initial_bl: List[str],
    items_to_add: Tuple[str, ...],
    apply_all: bool,
    force: bool,
    expected_final_wl: List[str],
    expected_final_bl: List[str],
    expect_modified: bool,
):
    """Tests adding items to the whitelist with various hierarchical and force options."""
    # Set initial state
    write_config(mock_pyproject_file, {"whitelist": initial_wl, "blacklist": initial_bl})

    modified = modify_tool_list(
        project_root=mock_pyproject_file.parent,
        tool_items_to_modify=items_to_add,
        target_list_name="whitelist",
        action="add",
        apply_all=apply_all,
        force=force,
    )

    assert modified is expect_modified

    # Verify final state
    final_wl = list_tool_list(mock_pyproject_file.parent, "whitelist")
    final_bl = list_tool_list(mock_pyproject_file.parent, "blacklist")
    assert final_wl == expected_final_wl
    assert final_bl == expected_final_bl


# Structure: (initial_wl, initial_bl, items_to_remove, apply_all, expected_final_wl, expected_final_bl, expect_modified)
# Force is not applicable to remove
MODIFY_REMOVE_TEST_CASES = [
    # --- Basic Remove --- #
    (["tool_a", "tool_b"], [], ("tool_a",), False, ["tool_b"], [], True),  # Remove simple
    (["tool_a"], [], ("tool_b",), False, ["tool_a"], [], False),  # Remove non-existent
    (["tool_a"], [], ("tool_a",), False, [], [], True),  # Remove last item
    (["tool_a:sub1", "tool_a:sub2"], [], ("tool_a:sub1",), False, ["tool_a:sub2"], [], True),  # Remove sub
    (["tool_a:sub1"], [], ("tool_a:sub2",), False, ["tool_a:sub1"], [], False),  # Remove non-existent sub
    (["tool_a:sub1:subsub1"], [], ("tool_a:sub1:subsub1",), False, [], [], True),  # Remove nested sub
    (["tool_a", "tool_a:sub1"], [], ("tool_a",), False, ["tool_a:sub1"], [], True),  # Remove explicit tool, keeps sub
    (["tool_a", "tool_a:sub1"], [], ("tool_a:sub1",), False, ["tool_a"], [], True),  # Remove sub, keeps explicit tool
    # --- Remove with --all / :* --- #
    (
        ["tool_a:*"],
        [],
        ("tool_a",),
        False,
        ["tool_a:*"],
        [],
        False,
    ),  # Remove simple when :* exists (no effect on flags)
    (["tool_a:*"], [], ("tool_a:*",), False, [], [], True),  # Remove :* when :* exists
    (["tool_a:*", "tool_b"], [], ("tool_a:*",), False, ["tool_b"], [], True),  # Remove :*
    (
        ["tool_a", "tool_a:sub1", "tool_a:sub2:*"],
        [],
        ("tool_a",),
        True,
        [],
        [],
        True,
    ),  # Remove simple --all (removes node)
    (
        ["tool_a", "tool_a:sub1", "tool_a:sub2:*"],
        [],
        ("tool_a:*",),
        True,
        [],
        [],
        True,
    ),  # Remove :* --all (removes node)
    (["tool_a:sub1:*", "tool_a:sub2"], [], ("tool_a:sub1",), True, ["tool_a:sub2"], [], True),  # Remove sub --all
    (
        ["tool_a:sub1:subsub1", "tool_a:sub2"],
        [],
        ("tool_a:sub1",),
        True,
        ["tool_a:sub2"],
        [],
        True,
    ),  # Remove sub --all (removes subsub)
    (["tool_a:sub1:*"], [], ("tool_a:sub1:*",), True, [], [], True),  # Remove sub:* --all
    # --- Remove interaction with other list (should have no effect) --- #
    (["tool_a"], ["tool_b"], ("tool_a",), False, [], ["tool_b"], True),  # Remove from WL, BL untouched
    (["tool_a:*"], ["tool_b"], ("tool_a:*",), True, [], ["tool_b"], True),  # Remove from WL --all, BL untouched
]


@pytest.mark.parametrize(
    "initial_wl, initial_bl, items_to_remove, apply_all, expected_final_wl, expected_final_bl, expect_modified",
    MODIFY_REMOVE_TEST_CASES,
)
def test_modify_remove_whitelist(
    mock_pyproject_file: Path,
    initial_wl: List[str],
    initial_bl: List[str],
    items_to_remove: Tuple[str, ...],
    apply_all: bool,
    expected_final_wl: List[str],
    expected_final_bl: List[str],
    expect_modified: bool,
):
    """Tests removing items from the whitelist with various hierarchical options."""
    # Set initial state
    write_config(mock_pyproject_file, {"whitelist": initial_wl, "blacklist": initial_bl})

    modified = modify_tool_list(
        project_root=mock_pyproject_file.parent,
        tool_items_to_modify=items_to_remove,
        target_list_name="whitelist",
        action="remove",
        apply_all=apply_all,
        force=False,  # Force is N/A for remove
    )

    assert modified is expect_modified

    # Verify final state
    final_wl = list_tool_list(mock_pyproject_file.parent, "whitelist")
    final_bl = list_tool_list(mock_pyproject_file.parent, "blacklist")
    assert final_wl == expected_final_wl
    assert final_bl == expected_final_bl


# endregion

# region Test list_tool_list
# ==================================================

LIST_TEST_CASES = [
    # Initial WL Content          Expected Output
    ([], []),  # Empty config
    (["tool_a", "tool_b:sub1"], ["tool_a", "tool_b:sub1"]),  # Simple list
    (["tool_b:sub1", "tool_a"], ["tool_a", "tool_b:sub1"]),  # Sorting
    (None, []),  # List key missing
    ("not a list", []),  # Wrong type
]


@pytest.mark.parametrize("initial_wl_content, expected_output_list", LIST_TEST_CASES)
def test_list_tool_list(mock_pyproject_file: Path, initial_wl_content: Any, expected_output_list: List[str]):
    """Tests reading the raw list."""
    # Setup based on initial_wl_content type
    if isinstance(initial_wl_content, str):
        # Write invalid type directly using tomlkit
        doc = tomlkit.parse(mock_pyproject_file.read_text())
        tool_table = doc.setdefault("tool", tomlkit.table())
        zt_table = tool_table.setdefault("zeroth-law", tomlkit.table())
        managed_table = zt_table.setdefault("managed-tools", tomlkit.table())
        managed_table["whitelist"] = initial_wl_content  # Write the invalid string
        mock_pyproject_file.write_text(tomlkit.dumps(doc), encoding="utf-8")
    elif isinstance(initial_wl_content, list):
        write_config(mock_pyproject_file, {"whitelist": initial_wl_content})
    else:  # Handles None case
        write_config(mock_pyproject_file, {})

    listed_items = list_tool_list(mock_pyproject_file.parent, "whitelist")
    assert listed_items == expected_output_list


def test_list_tool_list_file_not_found(tmp_path: Path):
    """Tests list_tool_list when pyproject.toml doesn't exist."""
    assert list_tool_list(tmp_path, "whitelist") == []


# endregion
