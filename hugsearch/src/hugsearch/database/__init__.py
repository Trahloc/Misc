"""
# PURPOSE: Public interface for database operations
## INTERFACES:
- setup_database(): Initialize and migrate database
- search(): Main search interface
- save_model(): Save or update a model
## DEPENDENCIES:
- schema: Database schema management
- models: Model CRUD operations
- search: Search functionality
- tags: Tag management
"""

from pathlib import Path
from typing import Dict, List, Optional, Union

from .schema import init_db, migrate_schema
from .models import upsert_model, get_model, delete_model
from .search import search_models
from .tags import search_by_tag, get_model_tags, get_all_tags


# Expose key functionality at package level
async def setup_database(db_path: Union[str, Path]) -> None:
    """Initialize and migrate database"""
    await init_db(db_path)
    await migrate_schema(db_path)


async def search(
    db_path: Union[str, Path],
    query: str,
    case_sensitive: bool = False,
    exact_match: bool = False,
    filters: Optional[Dict] = None,
) -> List[Dict]:
    """Search models with optional filters"""
    # Handle tag filter separately for efficiency
    if filters and "tags" in filters:
        tag_results = await search_by_tag(
            db_path, filters["tags"], case_sensitive=case_sensitive
        )
        if not query:  # If only filtering by tag
            return tag_results

        # Get IDs from tag search for filtering
        tag_ids = {r["id"] for r in tag_results}

        # Get text search results
        search_results = await search_models(
            db_path, query, case_sensitive, exact_match
        )

        # Return only results that match both conditions
        return [r for r in search_results if r["id"] in tag_ids]

    # No tag filter, just do text search
    return await search_models(db_path, query, case_sensitive, exact_match)


async def save_model(db_path: Union[str, Path], model_data: Dict) -> None:
    """Save or update a model"""
    await upsert_model(db_path, model_data)


# Re-export other useful functions
__all__ = [
    "setup_database",
    "search",
    "save_model",
    "get_model",
    "delete_model",
    "get_model_tags",
    "get_all_tags",
]
