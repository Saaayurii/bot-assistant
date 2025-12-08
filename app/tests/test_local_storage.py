import json
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open

@pytest.fixture
def _LocalStorage(tmp_path):
    '''Sets logger's test file path at import time'''
    from utils.queued_logger import QueuedLogger
    QueuedLogger(file_path=Path(f"{tmp_path}/data.jsonl"))
    from utils.local_storage import LocalStorage
    return LocalStorage

@pytest.fixture(autouse=True)
def reset_localstorage_class_vars(_LocalStorage):
    _LocalStorage._storage_path = None
    _LocalStorage._cache = None
    yield
    _LocalStorage._storage_path = None
    _LocalStorage._cache = None


def test_init_sets_storage_path_from_env(monkeypatch, _LocalStorage):
    monkeypatch.setenv("LOCAL_STORAGE", "/tmp/fake_path.json")
    storage = _LocalStorage()
    assert storage._storage_path == "/tmp/fake_path.json"


def test_init_raises_if_no_env(monkeypatch, _LocalStorage):
    monkeypatch.delenv("LOCAL_STORAGE", raising=False)
    from exceptions import MissingLocalStorageVariable
    with pytest.raises(MissingLocalStorageVariable, match="LOCAL_STORAGE env variable is not set"):
        _LocalStorage()


def test_get_storage_path_returns_path(monkeypatch, _LocalStorage):
    monkeypatch.setenv("LOCAL_STORAGE", "/tmp/fake_path.json")
    _LocalStorage()
    assert _LocalStorage.get_storage_path() == "/tmp/fake_path.json"


def test_get_storage_path_raises_if_uninitialized(_LocalStorage):
    with pytest.raises(ValueError, match="Storage path is not initialized"):
        _LocalStorage.get_storage_path()


def test_load_cache_reads_file(monkeypatch, _LocalStorage):
    data = {"hello": {"response": "world"}}
    fake_path = "/tmp/fake_path.json"
    monkeypatch.setenv("LOCAL_STORAGE", fake_path)

    m = mock_open(read_data=json.dumps(data))
    with patch("builtins.open", m):
        storage = _LocalStorage()
        cache = storage._load_cache()
    
    assert cache == data
    assert _LocalStorage._cache == data


def test_load_cache_raises_file_not_found(monkeypatch, _LocalStorage):
    fake_path = "/tmp/nonexistent.json"
    monkeypatch.setenv("LOCAL_STORAGE", fake_path)
    storage = _LocalStorage()
    from exceptions import FailedToOpenLocalStorage
    with pytest.raises(FailedToOpenLocalStorage, match="Knowledge base file not found"):
        storage._load_cache()


def test_load_cache_raises_invalid_json(monkeypatch, _LocalStorage):
    fake_path = "/tmp/invalid.json"
    monkeypatch.setenv("LOCAL_STORAGE", fake_path)
    m = mock_open(read_data="{invalid_json}")
    with patch("builtins.open", m):
        storage = _LocalStorage()
        from exceptions import FailedToSerializeLocalStorage
        with pytest.raises(FailedToSerializeLocalStorage, match="Invalid JSON format in knowledge base"):
            storage._load_cache()


def test_enter_returns_cache(monkeypatch, _LocalStorage):
    data = {"foo": "bar"}
    fake_path = "/tmp/fake_path.json"
    monkeypatch.setenv("LOCAL_STORAGE", fake_path)
    m = mock_open(read_data=json.dumps(data))
    with patch("builtins.open", m):
        storage = _LocalStorage()
        result = storage.__enter__()
        assert result == data
        assert _LocalStorage._cache == data


def test_exit_does_nothing(monkeypatch, _LocalStorage):
    fake_path = "/tmp/fake_path.json"
    monkeypatch.setenv("LOCAL_STORAGE", fake_path)
    storage = _LocalStorage()
    storage.__exit__(None, None, None)
