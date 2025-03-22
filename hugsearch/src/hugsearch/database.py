"""
# PURPOSE: Database operations facade
## INTERFACES:
- init_db(): Initialize database schema
- search_models(): Search for models
- upsert_model(): Insert or update a model
## DEPENDENCIES:
- aiosqlite: Async SQLite operations
"""
from pathlib import Path
from typing import Dict, List, Optional, Union

from .database.schema import init_db as _init_db
from .database.models import upsert_model as _upsert_model, get_model, delete_model
from .database.search import search_models as _search_models
from .database.tags import get_model_tags, get_all_tags, search_by_tag

# Re-export core functionality with original names
init_db = _init_db
upsert_model = _upsert_model

async def search_models(
    db_path: Union[str, Path],
    query: str,
    case_sensitive: bool = False,
    exact_match: bool = False,
    filters: Optional[Dict] = None
) -> List[Dict]:
    """Search models with optional filters"""
    # Handle tag filter separately for efficiency
    if filters and 'tags' in filters:
        tag_results = await search_by_tag(
            db_path,
            filters['tags'],
            case_sensitive=case_sensitive
        )
        if not query:  # If only filtering by tag
            return tag_results

        # Get IDs from tag search for filtering
        tag_ids = {r['id'] for r in tag_results}

        # Get text search results
        search_results = await _search_models(
            db_path, query, case_sensitive, exact_match
        )

        # Return only results that match both conditions
        return [r for r in search_results if r['id'] in tag_ids]

    # No tag filter, just do text search
    return await _search_models(db_path, query, case_sensitive, exact_match)

# Make commonly used functions available at package level
__all__ = [
    'init_db',
    'search_models',
    'upsert_model',
    'get_model',
    'delete_model',
    'get_model_tags',
    'get_all_tags'
]