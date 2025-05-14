# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/templates/example_module.py.template # Shortened
"""  # noqa: E501
# PURPOSE: [Briefly describe the purpose of this module file.]

## INTERFACES:
    # - [function_name(param_type) -> return_type]: [description]

## DEPENDENCIES:
    # - [module_path]: [What's needed.]
"""


def example_function(data: list[int]) -> list[int]:
    """
    PURPOSE: Filters out negative values and sorts the remaining non-negative integers.

    CONTEXT: No local imports.

    PARAMS:
      - data: A list of integers.

    RETURNS:
      - A sorted list of non-negative integers.
    """
    # Filter out negative values from the input
    filtered_data = [num for num in data if num >= 0]
    # Return the sorted list of non-negative integers
    return sorted(filtered_data)


"""
## KNOWN ERRORS: [List with severity.]

## IMPROVEMENTS: [This session's improvements.]

## FUTURE TODOs: [For next session. Consider further decomposition.]
"""
