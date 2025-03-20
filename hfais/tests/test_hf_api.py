import pytest
from hfais.hf_api import search_hf_models, cache_results, load_cached_results

def test_search_hf_models(monkeypatch):
    """Test the search_hf_models function."""
    def mock_get(*args, **kwargs):
        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return [{"name": "test-model", "size": 8, "creator": "test-creator"}]

        return MockResponse()

    monkeypatch.setattr("requests.get", mock_get)

    results = search_hf_models("test-query")
    assert len(results) == 1
    assert results[0]["name"] == "test-model"

def test_cache_and_load_results(tmp_path):
    """Test caching and loading of results."""
    cache_path = tmp_path / "cache.json"
    results = [{"name": "test-model", "size": 8, "creator": "test-creator"}]

    cache_results(results, cache_path)
    loaded_results = load_cached_results(cache_path)

    assert len(loaded_results) == 1
    assert loaded_results[0]["name"] == "test-model"