# FILE_LOCATION: https://github.com/Trahloc/Misc/blob/main/zeroth_law/src/zeroth_law/__init__.py
"""
# PURPOSE: Provide the public API for the Zeroth Law analyzer.

## INTERFACES:
  - analyze_file(file_path: str, update: bool = False, config: dict = None) -> dict: Analyze a single file.
  - analyze_directory(dir_path: str, recursive: bool = False, update: bool = False, config: dict = None) -> list: Analyze a directory.
  - create_skeleton(directory: str): creates a project skeleton

## DEPENDENCIES:
  - zeroth_law.analyzer: Core analysis logic.
  - zeroth_law.skeleton: creates project directories
"""
from zeroth_law.analyzer import analyze_file, analyze_directory
from zeroth_law.skeleton import create_skeleton

__all__ = ["analyze_file", "analyze_directory", "create_skeleton"]