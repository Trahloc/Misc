"""Tests for hierarchical list parsing utilities."""

import pytest
from pathlib import Path

from zeroth_law.common.hierarchical_utils import parse_to_nested_dict, check_list_conflicts, get_effective_status


def test_placeholder():
    """Placeholder test."""
    pass


def test_parse_to_nested_dict_basic():
    """Test basic parsing of single-level tools."""
    items = ["toolA", "toolB"]
    expected = {
        "toolA": {"_explicit": True, "_all": False},
        "toolB": {"_explicit": True, "_all": False},
    }
    assert parse_to_nested_dict(items) == expected


def test_parse_to_nested_dict_nested():
    """Test parsing of nested subcommands."""
    items = ["toolA:sub1:subsubA", "toolA:sub2"]
    expected = {
        "toolA": {
            "_explicit": False,  # Implicit parent
            "_all": False,
            "sub1": {"_explicit": False, "_all": False, "subsubA": {"_explicit": True, "_all": False}},
            "sub2": {"_explicit": True, "_all": False},
        }
    }
    assert parse_to_nested_dict(items) == expected


def test_parse_to_nested_dict_comma_handling():
    """Test comma handling for siblings (only last part)."""
    items = ["toolA:sub1,sub2", "toolB:subX"]
    expected = {
        "toolA": {
            "_explicit": False,
            "_all": False,
            "sub1": {"_explicit": True, "_all": False},
            "sub2": {"_explicit": True, "_all": False},
        },
        "toolB": {"_explicit": False, "_all": False, "subX": {"_explicit": True, "_all": False}},
    }
    assert parse_to_nested_dict(items) == expected


def test_parse_to_nested_dict_wildcard():
    """Test parsing of wildcards (':*')."""
    items = ["toolA:*", "toolB:sub1:*", "toolC:sub2"]  # Mix wildcard and explicit
    expected = {
        "toolA": {"_explicit": False, "_all": True},  # Wildcard applies here
        "toolB": {
            "_explicit": False,
            "_all": False,
            "sub1": {"_explicit": False, "_all": True},  # Wildcard applies here
        },
        "toolC": {"_explicit": False, "_all": False, "sub2": {"_explicit": True, "_all": False}},
    }
    assert parse_to_nested_dict(items) == expected


def test_parse_to_nested_dict_explicit_beats_wildcard_parent():
    """Test explicit child declaration overrides implicit wildcard parent"""
    # Although toolA isn't explicitly listed, the child implies its existence
    items = ["toolA:sub1"]
    expected = {"toolA": {"_explicit": False, "_all": False, "sub1": {"_explicit": True, "_all": False}}}
    assert parse_to_nested_dict(items) == expected


def test_parse_to_nested_dict_wildcard_beats_implicit_parent():
    """Test wildcard on parent is correctly set even if only child is listed."""
    items = ["toolA:sub1:*"]
    expected = {
        "toolA": {
            "_explicit": False,
            "_all": False,  # Parent isn't wildcard
            "sub1": {"_explicit": False, "_all": True},  # Subcommand is wildcard
        }
    }
    assert parse_to_nested_dict(items) == expected


def test_parse_to_nested_dict_empty_input():
    """Test empty list input."""
    assert parse_to_nested_dict([]) == {}


def test_parse_to_nested_dict_invalid_strings():
    """Test handling of potentially invalid strings (should be ignored or handled gracefully)."""
    # Current implementation likely ignores these or raises errors depending on split behavior.
    # Let's assume they are ignored or result in empty structures.
    items = ["", "::", ":sub1", "toolA:"]
    expected = {
        # ":sub1" might create {"": {"sub1": ...}} depending on split, let's assume ignored for now
        # "toolA:" might create {"toolA": {"": ...}} depending on split, let's assume ignored
    }
    # We might need to adjust the expected result based on actual behavior or refine the function
    # For now, assert it doesn't crash and produces an empty dict for these specific cases
    # or the structure if split(":") creates empty strings
    assert parse_to_nested_dict(items) == {}  # Assuming invalid entries are skipped


# --- Tests for check_list_conflicts --- #


def test_check_list_conflicts_no_conflicts():
    """Test when whitelist and blacklist have no overlapping explicit entries."""
    wl_tree = parse_to_nested_dict(["toolA", "toolB:sub1"])
    bl_tree = parse_to_nested_dict(["toolC", "toolB:sub2"])
    assert check_list_conflicts(wl_tree, bl_tree) == []


def test_check_list_conflicts_root_conflict():
    """Test conflict at the root level."""
    wl_tree = parse_to_nested_dict(["toolA"])
    bl_tree = parse_to_nested_dict(["toolA"])
    assert check_list_conflicts(wl_tree, bl_tree) == ["toolA"]


def test_check_list_conflicts_nested_conflict():
    """Test conflict at a nested level."""
    wl_tree = parse_to_nested_dict(["toolA:sub1:subsubA"])
    bl_tree = parse_to_nested_dict(["toolA:sub1:subsubA"])
    assert check_list_conflicts(wl_tree, bl_tree) == ["toolA:sub1:subsubA"]


def test_check_list_conflicts_multiple_conflicts():
    """Test multiple conflicts at different levels."""
    wl_tree = parse_to_nested_dict(["toolA", "toolB:sub1"])
    bl_tree = parse_to_nested_dict(["toolA", "toolB:sub1", "toolC"])
    # Need to sort the result for consistent comparison
    assert sorted(check_list_conflicts(wl_tree, bl_tree)) == sorted(["toolA", "toolB:sub1"])


def test_check_list_conflicts_wildcard_no_conflict():
    """Test that wildcards do not cause explicit conflicts."""
    wl_tree = parse_to_nested_dict(["toolA:*"])
    bl_tree = parse_to_nested_dict(["toolA:sub1"])
    assert check_list_conflicts(wl_tree, bl_tree) == []

    wl_tree = parse_to_nested_dict(["toolA:sub1"])
    bl_tree = parse_to_nested_dict(["toolA:*"])
    assert check_list_conflicts(wl_tree, bl_tree) == []


def test_check_list_conflicts_implicit_parent_no_conflict():
    """Test that implicitly defined parents don't cause conflicts."""
    # toolA is implicitly defined in wl_tree by its child
    wl_tree = parse_to_nested_dict(["toolA:sub1"])
    # toolA is explicitly defined in bl_tree
    bl_tree = parse_to_nested_dict(["toolA"])
    assert check_list_conflicts(wl_tree, bl_tree) == []  # No conflict as wl_tree toolA is not explicit


def test_check_list_conflicts_empty_trees():
    """Test with empty input trees."""
    assert check_list_conflicts({}, {}) == []
    assert check_list_conflicts(parse_to_nested_dict(["a"]), {}) == []
    assert check_list_conflicts({}, parse_to_nested_dict(["b"])) == []


# --- Tests for get_effective_status --- #

WL_TREE_1 = parse_to_nested_dict(["allow_tool", "allow_tool:sub1", "mixed_tool:allow_sub", "parent_allow:*"])
BL_TREE_1 = parse_to_nested_dict(["block_tool", "block_tool:sub1", "mixed_tool:block_sub", "parent_block:*"])

# Combine for complex scenarios
WL_TREE_COMPLEX = parse_to_nested_dict(
    [
        "toolA",  # Explicit W
        "toolB:sub1",  # Explicit W
        "toolC:*",  # Wildcard W
        "toolD:sub1:*",  # Wildcard W
        "toolE:sub1:subsubA",  # Explicit W
        "toolF:sub_allow",  # Explicit W
        "toolG:*",  # Wildcard W, but child is B
        "toolH:sub1",  # Explicit W, parent is B
    ]
)
BL_TREE_COMPLEX = parse_to_nested_dict(
    [
        "toolB:sub2",  # Explicit B
        "toolC:sub_block",  # Explicit B
        "toolD:sub2",  # Explicit B
        "toolE:sub2:*",  # Wildcard B
        "toolF:*",  # Wildcard B
        "toolG:sub_block",  # Explicit B
        "toolH:*",  # Wildcard B
    ]
)


@pytest.mark.parametrize(
    "sequence, wl_tree, bl_tree, expected_status",
    [
        # Basic Cases
        (["allow_tool"], WL_TREE_1, BL_TREE_1, "WHITELISTED"),
        (["block_tool"], WL_TREE_1, BL_TREE_1, "BLACKLISTED"),
        (["other_tool"], WL_TREE_1, BL_TREE_1, "UNSPECIFIED"),
        (["allow_tool", "sub1"], WL_TREE_1, BL_TREE_1, "WHITELISTED"),
        (["block_tool", "sub1"], WL_TREE_1, BL_TREE_1, "BLACKLISTED"),
        (["allow_tool", "sub_other"], WL_TREE_1, BL_TREE_1, "WHITELISTED"),  # Inherits from parent
        (["block_tool", "sub_other"], WL_TREE_1, BL_TREE_1, "BLACKLISTED"),  # Inherits from parent
        # Wildcard Inheritance
        (["parent_allow"], WL_TREE_1, BL_TREE_1, "UNSPECIFIED"),  # Parent itself isn't listed
        (["parent_allow", "anything"], WL_TREE_1, BL_TREE_1, "WHITELISTED"),
        (["parent_block"], WL_TREE_1, BL_TREE_1, "UNSPECIFIED"),
        (["parent_block", "anything"], WL_TREE_1, BL_TREE_1, "BLACKLISTED"),
        # Mixed Tool Precedence (Explicit child beats implicit parent)
        (["mixed_tool", "allow_sub"], WL_TREE_1, BL_TREE_1, "WHITELISTED"),
        (["mixed_tool", "block_sub"], WL_TREE_1, BL_TREE_1, "BLACKLISTED"),
        (["mixed_tool", "other_sub"], WL_TREE_1, BL_TREE_1, "UNSPECIFIED"),  # Neither explicit nor wildcard match
        # --- Complex Scenarios ---
        # Explicit W wins
        (["toolA"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "WHITELISTED"),
        (["toolB", "sub1"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "WHITELISTED"),
        # Explicit B wins
        (["toolB", "sub2"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "BLACKLISTED"),
        # Deeper path wins (Explicit W > Wildcard B)
        (["toolF", "sub_allow"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "WHITELISTED"),
        # Deeper path wins (Explicit B > Wildcard W)
        (["toolG", "sub_block"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "BLACKLISTED"),
        # Deeper path wins (Wildcard B > Wildcard W - assumed, needs confirmation)
        # Let's test toolE: sub1 is implicit W, sub2 is wildcard B
        (["toolE", "sub1", "subsubA"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "WHITELISTED"),  # Deepest explicit W
        (["toolE", "sub1", "other"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "UNSPECIFIED"),  # sub1 parent has no wildcard
        (["toolE", "sub2", "anything"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "BLACKLISTED"),  # Wildcard B takes precedence
        # Explicit beats wildcard (Explicit B > Wildcard W)
        (["toolC", "sub_block"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "BLACKLISTED"),
        # Wildcard inheritance check
        (["toolC", "other"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "WHITELISTED"),
        # Explicit beats wildcard (Explicit W > Wildcard B)
        (["toolH", "sub1"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "WHITELISTED"),
        # Wildcard inheritance check
        (["toolH", "other"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "BLACKLISTED"),
        # Unspecified
        (["toolZ", "sub1"], WL_TREE_COMPLEX, BL_TREE_COMPLEX, "UNSPECIFIED"),
    ],
)
def test_get_effective_status(sequence, wl_tree, bl_tree, expected_status):
    """Test various scenarios for get_effective_status precedence rules."""
    assert get_effective_status(sequence, wl_tree, bl_tree) == expected_status
