import pytest
from hfais.filters import filter_by_size, filter_by_creator

def test_filter_by_size():
    """Test filtering by size."""
    models = [
        {"name": "small-model", "size": 2},
        {"name": "large-model", "size": 10},
    ]
    filtered = filter_by_size(models, min_size=5, max_size=15)
    assert len(filtered) == 1
    assert filtered[0]["name"] == "large-model"

def test_filter_by_creator():
    """Test filtering by creator."""
    models = [
        {"name": "model-a", "creator": "Alice"},
        {"name": "model-b", "creator": "Bob"},
    ]
    filtered = filter_by_creator(models, creator="Alice")
    assert len(filtered) == 1
    assert filtered[0]["name"] == "model-a"