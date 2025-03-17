#!/usr/bin/env python3
"""
# PURPOSE: Fix cookiecutter template files to properly handle Jinja2 template syntax

## INTERFACES:
 - fix_template_file(file_path): Fix a single template file
 - fix_all_files(): Process all template files in the cookiecutter directory

## DEPENDENCIES:
 - os
 - glob
 - re
"""
import os
import re
import glob
from pathlib import Path

def fix_template_file(file_path):
    """Fix a cookiecutter template file by replacing problematic template syntax."""
    print(f"Processing {file_path}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Keep track if we made any changes
    original_content = content

    # Fix f-strings that include cookiecutter variables
    content = re.sub(
        r'f"[^"]*\{\{[^}]*\}[^}]*\}\}[^"]*"',
        lambda m: m.group(0).replace('{{ \\{', '{{ ').replace('}}} cli', '}} cli'),
        content
    )

    # Fix direct references to {directory}
    content = content.replace('{directory}', '{{ cookiecutter.project_name }}')

    # Fix triple-brace issue in non-f-string contexts
    content = re.sub(r'\{\{\{([^}]+)\}\}\}', r'{{ \1 }}', content)

    # Fix escaped braces in f-strings
    content = re.sub(r'f"[^"]*\{\{\\*\{([^}]+)\}\}\}[^"]*"', r'f"Hello from {{ cookiecutter.project_name }} cli"', content)

    # Fix any remaining escaped braces
    content = re.sub(r'\{\{\\*\{([^}]+)\}\}\}', r'{{ \1 }}', content)

    if content != original_content:
        print(f"Fixing {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def fix_all_files():
    """Process all template files in the cookiecutter template directory."""
    # Get the project root directory
    script_dir = Path(__file__).resolve().parent
    template_dir = script_dir / 'src' / 'zeroth_law' / 'cookiecutter-template'

    # Process files in the template directory
    for path in Path(template_dir).rglob('*'):
        if path.is_file() and not path.name == 'cookiecutter.json':
            try:
                fixed = fix_template_file(str(path))
                if fixed:
                    print(f"Fixed template syntax in {path.relative_to(template_dir)}")
            except Exception as e:
                print(f"Error processing {path}: {e}")

if __name__ == "__main__":
    fix_all_files()