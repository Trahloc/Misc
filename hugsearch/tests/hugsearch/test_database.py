"""
# PURPOSE: Tests for hugsearch.database search functionality

## INTERFACES:
- test_search_models: Test search with various queries
- test_case_sensitive_search: Test case sensitivity
- test_exact_match_search: Test exact matching
- test_filter_search: Test search filters

## DEPENDENCIES:
- pytest
- aiosqlite
- hugsearch.database
"""
import pytest
import pytest_asyncio
import aiosqlite
from pathlib import Path
import json
from hugsearch.database import init_db, upsert_model, search_models

@pytest_asyncio.fixture
async def test_db():
    """Provide a test database with sample data"""
    db_path = Path("test_models.db")
    try:
        # Clean up any leftover files from previous failed tests
        if db_path.exists():
            db_path.unlink()

        await init_db(db_path)
        async with aiosqlite.connect(db_path) as db:
            await db.commit()

        # Add test models
        test_models = [
            {
                "id": "model1",
                "name": "LLAMA 7B",
                "author": "meta",
                "description": "A foundational 7B parameter model",
                "tags": ["llm", "base-model"],
                "downloads": 1000,
                "likes": 500,
                "lastModified": "2024-01-01"
            },
            {
                "id": "model2",
                "name": "GPT2-medium",
                "author": "openai",
                "description": "Medium sized GPT2 model",
                "tags": ["gpt", "medium"],
                "downloads": 2000,
                "likes": 800,
                "lastModified": "2024-02-01"
            },
            {
                "id": "model3",
                "name": "CodeLlama-34b",
                "author": "meta",
                "description": "Code specialized 34B parameter model",
                "tags": ["llm", "code", "large"],
                "downloads": 1500,
                "likes": 600,
                "lastModified": "2024-03-01"
            }
        ]

        for model in test_models:
            await upsert_model(db_path, model)

        yield db_path

    finally:
        # Ensure cleanup happens even if test fails
        if db_path.exists():
            try:
                db_path.unlink()
            except Exception:
                # If we can't delete it now, mark it for deletion on interpreter exit
                import atexit
                atexit.register(lambda p=db_path: p.unlink(missing_ok=True))

@pytest.mark.asyncio
async def test_search_models(test_db):
    """Test basic search functionality"""
    # Test simple keyword search
    results = await search_models(test_db, "llama")
    assert len(results) == 2
    assert any(r["name"] == "LLAMA 7B" for r in results)
    assert any(r["name"] == "CodeLlama-34b" for r in results)

    # Test AND operation
    results = await search_models(test_db, "llama AND 7B")
    assert len(results) == 1
    assert results[0]["name"] == "LLAMA 7B"

    # Test OR operation
    results = await search_models(test_db, "gpt OR llama")
    assert len(results) == 3

@pytest.mark.asyncio
async def test_case_sensitive_search(test_db):
    """Test case sensitive search"""
    # Case insensitive (default)
    results = await search_models(test_db, "llama")
    assert len(results) == 2

    # Case sensitive
    results = await search_models(test_db, "LLAMA", case_sensitive=True)
    assert len(results) == 1
    assert results[0]["name"] == "LLAMA 7B"

@pytest.mark.asyncio
async def test_exact_match_search(test_db):
    """Test exact match search"""
    # Fuzzy match (default)
    results = await search_models(test_db, "llam")
    assert len(results) == 2

    # Exact match
    results = await search_models(test_db, "llam", exact_match=True)
    assert len(results) == 0

    results = await search_models(test_db, "LLAMA", exact_match=True)
    assert len(results) == 1

@pytest.mark.asyncio
async def test_filter_search(test_db):
    """Test search with filters"""
    # Test tag filter
    results = await search_models(test_db, "llama", filters={"tags": "code"})
    assert len(results) == 1
    assert results[0]["name"] == "CodeLlama-34b"

    # Test author filter
    results = await search_models(test_db, "llm", filters={"author": "meta"})
    assert len(results) == 2

    # Test multiple filters
    results = await search_models(test_db, "llm",
                                filters={"author": "meta", "tags": "code"})
    assert len(results) == 1
    assert results[0]["name"] == "CodeLlama-34b"
