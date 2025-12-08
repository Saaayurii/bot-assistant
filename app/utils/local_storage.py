import json
import os
from pathlib import Path

from exceptions import MissingLocalStorageVariable, FailedToOpenLocalStorage, FailedToSerializeLocalStorage, EmptyLocalStorage

class LocalStorage:
    """
    Loads a read-only knowledge base from a JSON file.
    Cached in memory for the lifetime of the process.
    """

    _storage_path: str | None = None
    _cache: dict | None = None

    def __init__(self, path: str | None = None):
        if self.__class__._storage_path is None:
            path = path or os.getenv("LOCAL_STORAGE")
            if not path:
                raise MissingLocalStorageVariable("LOCAL_STORAGE env variable is not set")
            self.__class__._storage_path = path

    @classmethod
    def get_storage_path(cls) -> str:
        '''Getter for the _storage_path'''
        if not cls._storage_path:
            raise ValueError("Storage path is not initialized")
        return cls._storage_path

    @classmethod
    def _load_cache(cls) -> dict:
        '''Load cache or open the local storage

        Opens the local storage file at first attempt and keeps it in the cache [_cache] afterwards.

        Returns:
            dict: The local storage as a dict.

        Raises:
            FailedToOpenLocalStorage: Knowledge base file not found
            FailedToSerializeLocalStorage: Invalid JSON format in knowledge base.
            EmptyLocalStorage: The _cache is empty and storage didn't return data
        '''

        if cls._cache is not None:
            return cls._cache
    
        path = Path(cls.get_storage_path()).resolve()
    
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FailedToOpenLocalStorage(f"Knowledge base file not found: {path}")
        except json.JSONDecodeError:
            raise FailedToSerializeLocalStorage(f"Invalid JSON format in knowledge base: {path}")
    
        if not data:
            raise EmptyLocalStorage(
                f"The _cache is empty and storage at [{path}] didn't return data"
            )
    
        cls._cache = data
        return data

    def __enter__(self) -> dict:
        return self._load_cache()

    def __exit__(self, exc_type, exc, tb):
        pass

