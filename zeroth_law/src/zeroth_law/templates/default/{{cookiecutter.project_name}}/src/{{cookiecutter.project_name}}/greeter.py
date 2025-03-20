# FILE_LOCATION: {{cookiecutter.project_name}}/src/{{cookiecutter.project_name}}/greeter.py
"""
# PURPOSE: Provides a function to generate greeting messages.

## INTERFACES:
 - greet_user(name: str = "world", formal: bool = False) -> str: Generates a greeting message.

## DEPENDENCIES:
 - None
"""

def greet_user(name: str = "world", formal: bool = False) -> str:
    """
    PURPOSE: Generates a personalized greeting message.

    PARAMS:
        name: The name to include in the greeting (defaults to "world")
        formal: Whether to use formal greeting style (defaults to False)

    RETURNS:
        A formatted greeting string
    """
    if formal:
        return f"Greetings, {name}!"
    else:
        return f"Hello, {name}!"

"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added detailed function documentation
 - Added footer documentation

## FUTURE TODOs:
 - Consider adding more greeting styles
 - Add input validation for name parameter
"""