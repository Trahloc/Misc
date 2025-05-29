# HugSearch Project Tasks and Notes

## Repeating Tasks
- [∞] [Critical] Adhere to the principles as laid out in Zeroth Law in [text](ZerothLawAIFramework.py.md)
- [∞] [High] Update todo.md every iteration
- [∞] [Medium] Create new TODOs to make sure we adhere to the Single Responsibility Principle
- [∞] [Low] Verify pytest tests for all files and features exist

## Current Test Status
- [x] [Critical] ~~Fix syntax error in database.py (unterminated triple quote at line 200)~~ - No syntax error found
- [x] [High] ~~Fix failing tests in:~~ All tests passing:
  - tests/hugsearch/commands/test_check.py
  - tests/hugsearch/commands/test_version.py
  - tests/hugsearch/test_exceptions.py
  - tests/hugsearch/test_logging.py
  - tests/hugsearch/test_types.py
  - tests/test_cli.py

## Implemented Features

### Core Components
- [x] SQLite database with FTS5 for efficient text search (database.py)
- [x] Scheduler for updates (scheduler.py)
  - Daily updates at 5 AM local time
  - Manual refresh capability
- [x] TUI using Textual framework (tui.py)
  - Mouse support
  - Real-time search
- [x] CLI interface for scripting (cli.py)

### Search Capabilities
- [x] Complex AND/OR queries
- [x] Case sensitivity controls
  - Double quotes for "case insensitive but exact"
  - Single quotes for 'case sensitive and exact'
- [x] Fuzzy matching by default
- [x] Exact matching option

### Data Management
- [x] SQLite + FTS5 implementation
- [x] Follow/unfollow creators
- [x] Automatic daily updates
- [x] Manual refresh functionality

## Pending Features

### High Priority
- [ ] Connection pooling for SQLite
- [ ] Metadata filters:
  - Model size
  - Framework
  - Task type
- [ ] Webhook listener for real-time updates
- [ ] Advanced TUI features:
  - Help screens
  - Detailed model views
- [ ] Configuration module for user preferences

### Medium Priority
- [ ] Advanced search result filtering
- [ ] Export functionality (JSON/CSV)
- [ ] Batch operations in CLI
- [ ] Search history tracking

### Low Priority
- [ ] Command completion in CLI
- [ ] Custom themes for TUI
- [ ] Analytics dashboard
- [ ] Import/export of followed creators

## Key Implementation Notes

### Important Files
- database.py: Core search and storage functionality
- scheduler.py: Update management
- tui.py: Terminal interface
- cli.py: Command-line interface

### API Endpoints & Methods
#### Hugging Face Hub API
- list_models(author: str) -> List[Dict]
- model_info(model_id: str) -> Dict
- Note: Check for rate limiting headers

### Database Schema
```sql
models:
  - id: TEXT PRIMARY KEY
  - name: TEXT NOT NULL
  - author: TEXT NOT NULL
  - last_modified: TEXT NOT NULL
  - metadata: TEXT NOT NULL (JSON)
  - downloads: INTEGER
  - likes: INTEGER
  - last_checked: TEXT NOT NULL

models_fts: (FTS5 virtual table)
  - name
  - author
  - description
  - tags

followed_creators:
  - author: TEXT PRIMARY KEY
  - last_checked: TEXT NOT NULL
```

### Search Query Syntax
- AND/OR operators: "llama AND (12B|34B|70B)"
- Case sensitivity:
  - "term" - case insensitive exact
  - 'term' - case sensitive exact
  - term - fuzzy match

### Important Dependencies
- textual>=0.47.1: Modern TUI framework
- aiosqlite>=0.19.0: Async SQLite support
- apscheduler>=3.10.4: Update scheduling
- rapidfuzz>=3.6.1: Fuzzy matching
- rich>=13.7.0: Text formatting
- huggingface-hub: Official HF API
- click: CLI framework

## Development Notes

### SQLite Performance
- Using FTS5 for full-text search
- JSON1 extension for metadata queries
- Consider implementing connection pooling
- Watch for concurrent access patterns

### TUI Design
- Textual chosen for:
  - Async support
  - Rich mouse interaction
  - Modern widget system
  - Active maintenance
  - Good documentation

### Update Strategy
- Daily updates at 5 AM local
- Support for webhooks (pending)
- Manual refresh granularity:
  - Individual models
  - All models from a creator
  - Search result sets

## Testing Priorities
- [ ] Fix database.py syntax errors
- [ ] Search accuracy
- [ ] Update reliability
- [ ] Concurrent access handling
- [ ] Memory usage with large datasets
- [ ] Test coverage for all command modules
- [ ] Integration tests for database operations
- [ ] Mock HuggingFace API calls in tests

## Future Considerations
- Integration with model card metadata
- Direct download capabilities
- Collaborative filtering for recommendations
- Git-like offline operation mode

## Completed
