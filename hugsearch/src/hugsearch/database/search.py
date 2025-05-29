"""
# PURPOSE: Handle text-based model search operations
## INTERFACES:
- search_by_name(): Search models by name
- search_by_description(): Full-text search in descriptions
## DEPENDENCIES:
- aiosqlite: Async SQLite operations
"""

from pathlib import Path
from typing import List, Dict, Optional, Union

import aiosqlite


async def search_by_name(
    db_path: Union[str, Path],
    name: str,
    case_sensitive: bool = False,
    exact_match: bool = False,
) -> List[Dict]:
    """Search models by name"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        if exact_match:
            if case_sensitive:
                cursor = await db.execute(
                    """
                    SELECT * FROM models
                    WHERE name = ?
                    OR name LIKE ?
                    OR name LIKE ?
                    OR name LIKE ?
                """,
                    (
                        name,  # Exact match
                        f"% {name} %",  # Word in middle
                        f"{name} %",  # Word at start
                        f"% {name}",  # Word at end
                    ),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM models
                    WHERE name_lower = ?
                    OR name_lower LIKE ?
                    OR name_lower LIKE ?
                    OR name_lower LIKE ?
                """,
                    (
                        name.lower(),
                        f"% {name.lower()} %",
                        f"{name.lower()} %",
                        f"% {name.lower()}",
                    ),
                )
        else:
            if case_sensitive:
                cursor = await db.execute(
                    """
                    SELECT * FROM models
                    WHERE name = ?
                    OR name GLOB ?
                    OR name GLOB ?
                    OR name GLOB ?
                """,
                    (
                        name,  # Exact match
                        f"* {name} *",  # Word in middle
                        f"{name} *",  # Word at start
                        f"* {name}",  # Word at end
                    ),
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM models
                    WHERE name_lower LIKE ?
                """,
                    (f"%{name.lower()}%",),
                )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def search_by_description(db_path: Union[str, Path], query: str) -> List[Dict]:
    """Search model descriptions using FTS5"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT m.* FROM models m
            JOIN model_descriptions d ON m.id = d.model_id
            WHERE d.description MATCH ?
            ORDER BY rank
        """,
            (f"{query}*",),
        )

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def search_models(
    db_path: Union[str, Path],
    query: str,
    case_sensitive: bool = False,
    exact_match: bool = False,
    filters: Optional[Dict] = None,
) -> List[Dict]:
    """Combined search across name, description and tags"""
    # Handle OR queries
    if " OR " in query:
        parts = [p.strip() for p in query.split(" OR ")]
        results = {}  # Use dict for deduplication
        for part in parts:
            part_results = await search_models(
                db_path, part, case_sensitive, exact_match, filters
            )
            for result in part_results:
                results[result["id"]] = result
        return list(results.values())

    # Handle AND queries
    if " AND " in query:
        parts = [p.strip() for p in query.split(" AND ")]
        results = None
        for i, part in enumerate(parts):
            part_results = await search_models(
                db_path, part, case_sensitive, exact_match, filters
            )
            if i == 0:
                results = {r["id"]: r for r in part_results}
            else:
                # Keep only results that match all parts
                curr_ids = {r["id"] for r in part_results}
                results = {
                    id_: result for id_, result in results.items() if id_ in curr_ids
                }
        return list(results.values()) if results else []

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        results = {}  # Use dict for deduplication

        # Search by name
        name_results = await search_by_name(db_path, query, case_sensitive, exact_match)
        for r in name_results:
            results[r["id"]] = r

        # Search by description (only for non-exact, case-insensitive searches)
        if not exact_match and not case_sensitive:
            desc_results = await search_by_description(db_path, query.lower())
            for r in desc_results:
                if r["id"] not in results:
                    results[r["id"]] = r

        # Search by tag
        if case_sensitive:
            cursor = await db.execute(
                """
                SELECT DISTINCT m.* FROM models m
                JOIN model_tags t ON m.id = t.model_id
                WHERE t.tag = ?
            """,
                (query,),
            )
        else:
            cursor = await db.execute(
                """
                SELECT DISTINCT m.* FROM models m
                JOIN model_tags t ON m.id = t.model_id
                WHERE t.tag_lower = ?
            """,
                (query.lower(),),
            )
        tag_results = await cursor.fetchall()
        for r in tag_results:
            if r["id"] not in results:
                results[r["id"]] = dict(r)

        # Apply filters if provided
        if filters:
            filtered_ids = set(results.keys())  # Start with all current results

            # Apply tag filter
            if "tags" in filters:
                tag = filters["tags"]
                # Match tag using case sensitivity setting
                if case_sensitive:
                    cursor = await db.execute(
                        """
                        SELECT DISTINCT model_id FROM model_tags
                        WHERE tag = ?
                    """,
                        (tag,),
                    )
                else:
                    cursor = await db.execute(
                        """
                        SELECT DISTINCT model_id FROM model_tags
                        WHERE tag_lower = ?
                    """,
                        (tag.lower(),),
                    )
                tag_model_ids = {row[0] for row in await cursor.fetchall()}
                filtered_ids &= tag_model_ids

            # Apply author filter
            if "author" in filters:
                author = filters["author"]
                # Match author using case sensitivity setting
                if case_sensitive:
                    cursor = await db.execute(
                        """
                        SELECT id FROM models
                        WHERE author = ?
                    """,
                        (author,),
                    )
                else:
                    cursor = await db.execute(
                        """
                        SELECT id FROM models
                        WHERE author_lower = ?
                    """,
                        (author.lower(),),
                    )
                author_model_ids = {row[0] for row in await cursor.fetchall()}
                filtered_ids &= author_model_ids

            # Filter results to only those matching all filters
            results = {
                id_: result for id_, result in results.items() if id_ in filtered_ids
            }

        return list(results.values())
