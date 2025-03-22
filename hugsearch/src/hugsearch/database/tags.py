"""
# PURPOSE: Handle model tag operations
## INTERFACES:
- get_model_tags(): Get tags for a model
- search_by_tag(): Find models with specific tag
- get_all_tags(): List all known tags
## DEPENDENCIES:
- aiosqlite: Async SQLite operations
"""
from pathlib import Path
from typing import List, Dict, Union

import aiosqlite

async def get_model_tags(db_path: Union[str, Path], model_id: str) -> List[str]:
    """Get all tags for a specific model"""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT tag FROM model_tags WHERE model_id = ? ORDER BY tag",
            (model_id,)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def search_by_tag(
    db_path: Union[str, Path],
    tag: str,
    case_sensitive: bool = False
) -> List[Dict]:
    """Find all models with a specific tag"""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        if case_sensitive:
            cursor = await db.execute("""
                SELECT m.* FROM models m
                JOIN model_tags t ON m.id = t.model_id
                WHERE t.tag = ?
                ORDER BY m.name
            """, (tag,))
        else:
            cursor = await db.execute("""
                SELECT m.* FROM models m
                JOIN model_tags t ON m.id = t.model_id
                WHERE t.tag_lower = ?
                ORDER BY m.name
            """, (tag.lower(),))

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_all_tags(
    db_path: Union[str, Path],
    include_counts: bool = False
) -> Union[List[str], List[Dict[str, Union[str, int]]]]:
    """Get all known tags, optionally with usage counts"""
    async with aiosqlite.connect(db_path) as db:
        if include_counts:
            cursor = await db.execute("""
                SELECT tag, COUNT(*) as count
                FROM model_tags
                GROUP BY tag
                ORDER BY count DESC, tag
            """)
            rows = await cursor.fetchall()
            return [{"tag": row[0], "count": row[1]} for row in rows]
        else:
            cursor = await db.execute(
                "SELECT DISTINCT tag FROM model_tags ORDER BY tag"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]