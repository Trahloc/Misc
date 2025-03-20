# FILE_LOCATION: hugsearch/tests/test_project_setup.py
"""
# PURPOSE: Tests to verify proper project setup and customization.

## INTERFACES:
#   test_project_name_customized: Check if project name has been customized
#   test_author_info_customized: Check if author info has been customized

## DEPENDENCIES:
#   pytest
#   pyproject.toml
"""
import os
import pytest
import warnings
import tomli
from pathlib import Path


def _get_pyproject_data():
    """Helper function to read pyproject.toml data"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    if not pyproject_path.exists():
        warnings.warn(f"Could not find pyproject.toml at {pyproject_path}")
        return {}
    
    try:
        with open(pyproject_path, "rb") as f:
            return tomli.load(f)
    except Exception as e:
        warnings.warn(f"Error reading pyproject.toml: {str(e)}")
        return {}


def test_project_name_customized():
    """
    PURPOSE: Verify that the project name has been customized from the default value.
    
    CONTEXT: This test checks if the project name is still set to the default template value.
    
    PARAMS: None
    
    RETURNS: None
    """
    pyproject_data = _get_pyproject_data()
    if not pyproject_data:
        # Skip if we couldn't read the file
        pytest.skip("Could not read pyproject.toml")
    
    project_name = pyproject_data.get("project", {}).get("name", "")
    
    # Check both for the default value and for the uncustomized template variable
    if project_name == "my_project" or project_name == "hugsearch":
        warnings.warn(
            f"\nDEFAULT PROJECT NAME DETECTED: Project name is still set to '{project_name}'.\n"
            "This suggests the project was not properly customized when created.\n"
            "You should update the name in pyproject.toml to match your actual project name."
        )


def test_author_info_customized():
    """
    PURPOSE: Verify that the author information has been customized from default values.
    
    CONTEXT: This test checks if author name and email are still set to template defaults.
    
    PARAMS: None
    
    RETURNS: None
    """
    pyproject_data = _get_pyproject_data()
    if not pyproject_data:
        # Skip if we couldn't read the file
        pytest.skip("Could not read pyproject.toml")
    
    authors = pyproject_data.get("project", {}).get("authors", [])
    
    for author in authors:
        author_name = author.get("name", "")
        author_email = author.get("email", "")
        
        # Check for default values and uncustomized template variables
        if author_name == "Your Name" or author_name == "Zeroth Law Developer":
            warnings.warn(
                f"\nDEFAULT AUTHOR NAME DETECTED: Author name is still set to '{author_name}'.\n"
                "This suggests the project was not properly customized when created.\n"
                "You should update the author name in pyproject.toml."
            )
        
        if author_email == "your.email@example.com" or author_email == "developer@example.com":
            warnings.warn(
                f"\nDEFAULT EMAIL DETECTED: Author email is still set to '{author_email}'.\n"
                "This suggests the project was not properly customized when created.\n"
                "You should update the email in pyproject.toml."
            )


def test_project_consistency():
    """
    PURPOSE: Verify that the project name in pyproject.toml matches the actual directory name.
    
    CONTEXT: This test checks if the project name in pyproject.toml is consistent with the
    name of the project directory, helping detect mismatches between --skel naming and default values.
    
    PARAMS: None
    
    RETURNS: None
    """
    pyproject_data = _get_pyproject_data()
    if not pyproject_data:
        # Skip if we couldn't read the file
        pytest.skip("Could not read pyproject.toml")
    
    project_name = pyproject_data.get("project", {}).get("name", "")
    
    # Get the actual directory name (should be the real project name)
    # Go up two levels from the test file to get the project root directory
    project_dir = Path(__file__).parent.parent
    actual_project_name = project_dir.name
    
    if project_name != actual_project_name and project_name != "":
        warnings.warn(
            f"\nPROJECT NAME MISMATCH DETECTED: Project name in pyproject.toml ('{project_name}') "
            f"does not match the actual directory name ('{actual_project_name}').\n"
            "This suggests that the project name in pyproject.toml was not properly set when using --skel.\n"
            "You should update the project name in pyproject.toml to match your actual project name."
        )


"""
## KNOWN ERRORS: None

## IMPROVEMENTS:
 - Added tests to detect uncustomized project defaults
 - Warning-based approach avoids breaking legitimate tests

## FUTURE TODOs:
 - Add more checks for other configurable values
 - Consider loading configuration from a separate file
""" 