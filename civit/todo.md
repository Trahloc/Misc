# TODO Checklist

## Forever TODOs (evaluated every time code or tasks are changed)

[∞] [Critical] AI is the Lead Developer, be proactive. Follow the Zeroth Law defined in [ZerothLawAIFramework.py.md](/docs/ZerothLawAIFramework.py.md)

[∞] [High] After completing any task:
    • Mark the task as done in todo.md
    • When a feature is modified make sure pytest tests are updated as well
    • Add notes if anything unexpected happened

[∞] [Medium] When adding or changing a feature:
    • Check if it violates the Single Responsibility Principle (SRP)
    • If it does, create a new TODO: "[Refactor] Split [feature_name] to follow SRP"

[∞] [High] For every feature in the codebase:
    • Check if there is a pytest for it
    • If missing, create a TODO: "[Test] Write pytest for [feature_name]"

## Current Tasks
- [ ] Add a progress bar for downloads
- [ ] Add better error handling for network issues
- [ ] Implement rate limiting for API requests

## Blocked Tasks

## Completed Tasks

## Rejected Tasks
- [!] Add parallel download support

## Future TODOs
- [ ] Extract error handling into a separate module
- [ ] Consider using property-based testing for more robust validation
- [ ] Support batch downloads with a queue system
- [ ] Improve the retry mechanism with exponential but reasonable maximum backoff
