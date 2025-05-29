# Shared test data structures for hierarchical/list utils tests

NESTED_EXAMPLE = {
    "toolA": {
        "_explicit": False,
        "_all": False,
        "sub1": {
            "_explicit": False,
            "_all": False,
            "subsubA": {"_explicit": True, "_all": False},
        },
    }
}

NESTED_EXAMPLE_VARIANT = {
    "toolA": {
        "_explicit": False,
        "_all": False,
        "sub1": {
            "_explicit": False,
            "_all": True,
        },
    }
}
# Add more as needed for other deduplicated test cases.
