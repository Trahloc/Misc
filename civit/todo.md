# TODO Checklist

## Forever TODOs (evaluated every time code or tasks are changed)

[∞] [Critical] AI is the Lead Developer, be proactive. Follow the Zeroth Law defined in [ZerothLawAIFramework.py.md](/docs/ZerothLawAIFramework.py.md)

[∞] [High] After completing any task:
    • Mark the task as done in todo.md
    • Add notes if anything unexpected happened

[∞] [Medium] When adding or changing a feature:
    • Check if it violates the Single Responsibility Principle (SRP)
    • If it does, create a new TODO: "[Refactor] Split [feature_name] to follow SRP"

[∞] [High] For every feature in the codebase:
    • Check if there is a pytest for it
    • If missing, create a TODO: "[Test] Write pytest for [feature_name]"

## Current Tasks

## Blocked Tasks

## Completed Tasks
[x] [Fix] Improve download timeout handling
    • Separated connection and read timeouts
    • HEAD request: 30s connection, 30s read timeout
    • GET request: 30s connection, 60s read timeout between chunks
    • Total download time now unlimited as long as data keeps flowing
    Notes: This prevents timeouts during large downloads while ensuring responsiveness

[x] [Critical] Fix package installation and import issues
    • Fixed import paths in download_handler.py to use relative imports
    • Removed unused extract_filename_from_response from __init__.py
    • Simplified __init__.py to avoid silent failures
    • Package now installs and runs correctly
    Notes: The package can now be installed and run from any directory

[x] [Critical] Verify and fix tests making real network calls
[x] [Critical] Fix test failures from recent pytest run
[x] [Improvement] Add support for resumable downloads
[x] [Improvement] Add CLI tests and fix test_resumable_download.py
[x] [Fix] Fix remaining failing tests in pytest run
[x] [Fix] Fix second round of test failures
[x] [Fix] Fix third round of test failures
[x] [Fix] Implement verbosity counting and fix CLI tests