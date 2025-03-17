# Zeroth Law AI-Driven Development Implementation

This directory contains practical implementations and tools for applying the Zeroth Law of AI-Driven Development framework. The framework establishes fundamental quality principles for technical hobbyists using AI tools to generate and maintain code.

## Contents

- `ZerothLawAI.md` - The core framework documentation
- `zeroth_law_analyzer.py` - Python tool to analyze code for Zeroth Law compliance (now supports multi-file analysis)
- `zeroth_law_template.py` - Example template showing perfect Zeroth Law compliance

## Getting Started

### Using the Analyzer

The analyzer tool can check existing code for compliance with Zeroth Law principles:

```bash
# Analyze a single file:
python zeroth_law_analyzer.py /path/to/your/file.py

# Analyze all Python files in a directory:
python zeroth_law_analyzer.py /path/to/your/directory --pattern "*.py"

# Recursively scan directories:
python zeroth_law_analyzer.py /path/to/your/directory --pattern "**/*.py" --recursive

# Add a Zeroth Law header to file(s):
python zeroth_law_analyzer.py /path/to/your/file.py --add-header "Brief description of file purpose"

# Update the assessment footer after making improvements:
python zeroth_law_analyzer.py /path/to/your/file.py --update-footer

# For directory-based operations, header/footer actions apply to all valid files.
```

### Using the Template

When creating new files, you can use `zeroth_law_template.py` as a starting point. It demonstrates:

- Proper header documentation
- Interface documentation
- Function and class organization
- Semantic naming
- Self-contained code with minimal external dependencies

## Workflow Integration

1. Start each file with the proper Zeroth Law header.
2. Implement code following the framework principles.
3. Analyze code regularly using the analyzer tool.
4. Add an assessment footer after implementation.
5. Update the header status for the next development session.