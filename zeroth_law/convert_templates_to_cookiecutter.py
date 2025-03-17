#!/usr/bin/env python3
"""
# PURPOSE: Convert existing template files to cookiecutter format.
"""
import os
import re
import shutil

def convert_template_to_cookiecutter(src_path, dest_path):
    """Convert a template file to cookiecutter format."""
    # Ensure the destination directory exists
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    # Read the template file
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace {directory} with {{cookiecutter.project_name}}
    content = content.replace('{directory}', '{{cookiecutter.project_name}}')

    # Handle escaped curly braces in f-strings (like f"Hello from {{directory}} cli")
    # This pattern looks for {{ followed by text and }} which is likely an f-string escape
    pattern = r'{{([^{}]+)}}'

    # Replace with triple braces to handle cookiecutter's double braces
    content = re.sub(pattern, r'{{\{\1}}}', content)

    # Handle {default_config} placeholder
    content = content.replace('{default_config}', '{{cookiecutter.default_config}}')

    # Save the converted content
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Converted: {src_path} -> {dest_path}")

def process_all_templates():
    """Process all template files in the project."""
    src_template_dir = 'src/zeroth_law/templates'
    dest_template_dir = 'src/zeroth_law/cookiecutter-template/template/{{cookiecutter.project_name}}'

    # Process regular files (not in tests directory)
    for filename in os.listdir(src_template_dir):
        if filename == 'tests':  # Skip tests directory for now
            continue

        src_path = os.path.join(src_template_dir, filename)
        if os.path.isfile(src_path):
            # Determine destination path
            if filename == 'pyproject.toml.template' or filename == 'README.md.template' or filename.startswith('.'):
                # These go in the root project directory
                dest_filename = filename.replace('.template', '')
                dest_path = os.path.join('src/zeroth_law/cookiecutter-template/template/{{cookiecutter.project_name}}', dest_filename)
            else:
                # These go in the src/project_name directory
                dest_filename = filename.replace('.template', '')
                dest_path = os.path.join(dest_template_dir, 'src', '{{cookiecutter.project_name}}', dest_filename)

            convert_template_to_cookiecutter(src_path, dest_path)

    # Process test files
    tests_src_dir = os.path.join(src_template_dir, 'tests')
    tests_dest_dir = os.path.join(dest_template_dir, 'tests')

    if os.path.exists(tests_src_dir):
        for filename in os.listdir(tests_src_dir):
            src_path = os.path.join(tests_src_dir, filename)
            if os.path.isfile(src_path):
                dest_filename = filename.replace('.template', '')
                dest_path = os.path.join(tests_dest_dir, dest_filename)
                convert_template_to_cookiecutter(src_path, dest_path)

if __name__ == "__main__":
    # Change to the project root directory
    os.chdir('/home/trahloc/code/Misc/zeroth_law')
    process_all_templates()
    print("Conversion completed successfully!")