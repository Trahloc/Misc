# FILE: tools/autoinit.py
"""
# PURPOSE: Automatically generates and updates __init__.py files based on module contents.

## INTERFACES: main() -> int: Main entry point for the tool

## DEPENDENCIES:
  - os: For file system operations
  - pathlib: For file path handling
  - re: For regular expression parsing
  - argparse: For command-line argument parsing
  - toml: For reading pyproject.toml configuration

## TODO:
  - Add support for different export patterns
  - Implement tests for the tool
"""

import os
import re
import sys
import toml
import argparse
from pathlib import Path
from typing import List, Dict, Set, Optional

def parse_arguments() -> argparse.Namespace:
    """
    PURPOSE: Parse command-line arguments for the autoinit tool.
    
    RETURNS:
    argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Automatically generate and update __init__.py files."
    )
    parser.add_argument(
        "--config", 
        help="Path to pyproject.toml file", 
        default="pyproject.toml"
    )
    parser.add_argument(
        "--src-dir", 
        help="Source directory to scan", 
        default=None
    )
    parser.add_argument(
        "--dry-run", 
        help="Show what would be done without making changes", 
        action="store_true"
    )
    parser.add_argument(
        "--verbose", 
        help="Show detailed output", 
        action="store_true"
    )
    
    return parser.parse_args()

def read_config(config_path: str) -> Dict:
    """
    PURPOSE: Read and parse the pyproject.toml configuration file.
    
    PARAMS:
    config_path: str - Path to the pyproject.toml file
    
    RETURNS:
    Dict: Configuration dictionary
    """
    try:
        return toml.load(config_path)
    except Exception as e:
        print(f"Error reading config file {config_path}: {e}", file=sys.stderr)
        return {}

def get_source_dir(config: Dict, cmd_src_dir: Optional[str]) -> str:
    """
    PURPOSE: Determine the source directory from arguments or configuration.
    
    PARAMS:
    config: Dict - Configuration dictionary
    cmd_src_dir: Optional[str] - Source directory from command line
    
    RETURNS:
    str: Source directory path
    """
    if cmd_src_dir:
        return cmd_src_dir
    
    # Try to get from config
    if "tool" in config and "autoinit" in config["tool"]:
        if "src_dir" in config["tool"]["autoinit"]:
            return config["tool"]["autoinit"]["src_dir"]
    
    # Default to src if exists, otherwise current directory
    if os.path.isdir("src"):
        return "src"
    return "."

def get_ignore_dirs(config: Dict) -> List[str]:
    """
    PURPOSE: Get directories to ignore from configuration.
    
    PARAMS:
    config: Dict - Configuration dictionary
    
    RETURNS:
    List[str]: List of directories to ignore
    """
    if "tool" in config and "autoinit" in config["tool"]:
        if "ignore_dirs" in config["tool"]["autoinit"]:
            return config["tool"]["autoinit"]["ignore_dirs"]
    
    # Default ignored directories
    return ["tests", "docs", "examples", "__pycache__"]

def find_python_modules(directory: str, ignore_dirs: List[str]) -> Dict[str, List[str]]:
    """
    PURPOSE: Find Python modules in the specified directory.
    
    PARAMS:
    directory: str - Directory to scan
    ignore_dirs: List[str] - Directories to ignore
    
    RETURNS:
    Dict[str, List[str]]: Dictionary mapping directories to module files
    """
    modules = {}
    
    for root, dirs, files in os.walk(directory):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        # Skip directories with no Python files
        python_files = [f for f in files if f.endswith(".py") and f != "__init__.py"]
        if not python_files:
            continue
        
        # Add to modules dict
        rel_path = os.path.relpath(root, directory)
        if rel_path == ".":
            rel_path = ""
            
        modules[rel_path] = python_files
    
    return modules

def extract_function_info(file_path: Path) -> List[Dict[str, str]]:
    """
    PURPOSE: Extract function information from a Python file.
    
    PARAMS:
    file_path: Path - Path to the Python file
    
    RETURNS:
    List[Dict[str, str]]: List of function information dictionaries
    """
    functions = []
    with open(file_path, "r") as f:
        content = f.read()
    
    # Find all function definitions
    func_pattern = r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*->\s*([^:]+):\s*(?:\"\"\"|\'\'\')(?:\s*PURPOSE:\s*([^\"\']+))?"
    matches = re.finditer(func_pattern, content, re.MULTILINE)
    
    for match in matches:
        if match.group(1).startswith("_"):
            continue  # Skip private functions
            
        func_info = {
            "name": match.group(1),
            "params": match.group(2).strip(),
            "return_type": match.group(3).strip(),
            "purpose": match.group(4).strip() if match.group(4) else "No description provided"
        }
        functions.append(func_info)
    
    return functions

def generate_init_content(directory: str, modules: List[str], base_path: str) -> str:
    """
    PURPOSE: Generate content for an __init__.py file.
    
    PARAMS:
    directory: str - Directory path
    modules: List[str] - List of module files
    base_path: str - Base path for import statements
    
    RETURNS:
    str: Generated __init__.py content
    """
    module_path = directory.replace(os.sep, ".")
    if module_path and not module_path.startswith("."):
        module_path = "." + module_path
        
    public_functions = []
    imports = []
    
    for module in modules:
        module_name = os.path.splitext(module)[0]
        
        # Skip __init__ and __main__
        if module_name in ("__init__", "__main__"):
            continue
            
        # Add import statement
        imports.append(f"from {module_path}.{module_name} import *")
        
        # Extract function info for documentation
        module_path_obj = Path(base_path) / directory / module
        functions = extract_function_info(module_path_obj)
        for func in functions:
            public_functions.append(f"  - {func['name']}({func['params']}) -> {func['return_type']}: {func['purpose']}")
    
    # Build the __init__.py content
    content = [
        f"# FILE: {os.path.join(base_path, directory, '__init__.py')}",
        '"""',
        f"# PURPOSE: Provides public API for the {directory if directory else 'tmux_manager'} module.",
        "",
        "## INTERFACES:"
    ]
    
    # Add function documentation
    if public_functions:
        content.extend(public_functions)
    else:
        content.append("  None")
    
    content.extend([
        "",
        "## DEPENDENCIES:",
        f"  - {', '.join([os.path.splitext(m)[0] for m in modules if not m.startswith('__')])}" if modules else "  None",
        "",
        "## TODO:",
        "  - Update documentation as module evolves",
        '"""',
        "",
        "# Version information",
        "__version__ = \"0.1.0\"",
        ""
    ])
    
    # Add imports
    content.extend(imports)
    
    # Add module all variable
    all_funcs = []
    for func in public_functions:
        match = re.search(r"\s*-\s*([a-zA-Z_][a-zA-Z0-9_]*)", func)
        if match:
            all_funcs.append(match.group(1))
    
    if all_funcs:
        content.extend([
            "",
            "# Explicitly define public API",
            f"__all__ = {str(all_funcs)}"
        ])
    
    content.extend([
        "",
        '"""',
        "## KNOWN ERRORS:",
        "- No known errors",
        "",
        "## IMPROVEMENTS:",
        "- Auto-generated by autoinit tool",
        "",
        "## FUTURE TODOs:",
        "- Update as module evolves",
        '"""'
    ])
    
    return "\n".join(content)

def update_init_files(modules_dict: Dict[str, List[str]], base_path: str, dry_run: bool, verbose: bool) -> int:
    """
    PURPOSE: Update __init__.py files for the modules.
    
    PARAMS:
    modules_dict: Dict[str, List[str]] - Dictionary mapping directories to module files
    base_path: str - Base path for the modules
    dry_run: bool - If True, don't write files, just show what would be done
    verbose: bool - If True, show detailed output
    
    RETURNS:
    int: Number of files updated
    """
    updated = 0
    
    for directory, modules in modules_dict.items():
        init_path = os.path.join(base_path, directory, "__init__.py")
        new_content = generate_init_content(directory, modules, base_path)
        
        # Check if file exists and if content has changed
        if os.path.exists(init_path):
            with open(init_path, "r") as f:
                current_content = f.read()
                
            if current_content.strip() == new_content.strip():
                if verbose:
                    print(f"No changes needed for {init_path}")
                continue
                
            action = "Update"
        else:
            action = "Create"
        
        # Create or update the file
        if dry_run:
            print(f"Would {action.lower()} {init_path}")
            if verbose:
                print(f"Content would be:\n{new_content}\n")
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(init_path), exist_ok=True)
            
            with open(init_path, "w") as f:
                f.write(new_content)
                
            print(f"{action}d {init_path}")
            updated += 1
    
    return updated

def main() -> int:
    """
    PURPOSE: Main entry point for the autoinit tool.
    
    RETURNS:
    int: Exit code (0 for success, non-zero for error)
    """
    args = parse_arguments()
    
    # Read configuration
    config = read_config(args.config)
    
    # Get source directory and ignored directories
    src_dir = get_source_dir(config, args.src_dir)
    ignore_dirs = get_ignore_dirs(config)
    
    if args.verbose:
        print(f"Source directory: {src_dir}")
        print(f"Ignored directories: {ignore_dirs}")
    
    # Find Python modules
    modules_dict = find_python_modules(src_dir, ignore_dirs)
    
    if not modules_dict:
        print("No Python modules found")
        return 0
    
    if args.verbose:
        print("Found modules:")
        for directory, modules in modules_dict.items():
            print(f"  {directory or '.'}: {', '.join(modules)}")
    
    # Update __init__.py files
    updated = update_init_files(modules_dict, src_dir, args.dry_run, args.verbose)
    
    if args.dry_run:
        print(f"Would update {updated} __init__.py files")
    else:
        print(f"Updated {updated} __init__.py files")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

"""
## KNOWN ERRORS:
- May not correctly parse complex function definitions
- Does not handle nested function definitions

## IMPROVEMENTS:
- Automatically detects Python modules and generates __init__.py files
- Extracts function information from docstrings
- Supports dry run and verbose modes

## FUTURE TODOs:
- Add support for class exports
- Improve function detection regex
- Add tests for the tool
- Support custom templates for __init__.py files
"""