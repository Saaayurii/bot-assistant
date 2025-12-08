from typing import Any, Callable
from pydantic import BaseModel
from datetime import datetime
from dataclasses import is_dataclass, fields
import uuid
import json

class SerializeAdapter:
    '''
    Wrapper that encapsulates _Decoder and _Encoder.
    '''
    class _Decoder(json.JSONDecoder):
        '''Custom decoder for python build-in json library'''
        @staticmethod
        def from_dict(dtos: list[type[BaseModel]]) -> Callable[[Any], Any]:
            def decode(d: Any) -> Any:
                if isinstance(d, dict):
                    if "__class__" in d:
                        for dto in dtos:
                            if d["__class__"] == dto.__name__:
                                dto_data = {k: decode(v) for k, v in d.items() if k != "__class__"} or {}
                                return dto(**dto_data)
                    return {k: decode(v) for k, v in d.items()} or {}
                elif isinstance(d, list):
                    return [decode(item) for item in d] or []
                return d
    
            return decode

    class _Encoder(json.JSONEncoder):
        '''Customo encoder for python build-in json library'''
        def default(self, obj):
            return self._encode(obj)

        def _encode(self, obj):
            if isinstance(obj, BaseModel):
                # Recursively encode DTOs while preserving structure
                return {str(key): self._encode(getattr(obj, key)) for key in obj.__class__.model_fields} | {"__class__": obj.__class__.__name__}
            if is_dataclass(obj) and not isinstance(obj, type):
                result = {}
                for f in fields(obj):
                    result[f.name] = self._encode(getattr(obj, f.name))
                result["__class__"] = obj.__class__.__name__
                return result            
            if isinstance(obj, list):
                return [self._encode(item) for item in obj] 
            if isinstance(obj, dict):
                return {str(key): self._encode(value) for key, value in obj.items()}
            if isinstance(obj, uuid.UUID):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
           
            try:
                return super().default(obj)
            except TypeError:
                return str(obj)

    def serialize(self, raw_data) -> str:
        '''Wrapper for serialization.

        Args:
            raw_data (Any): It might be anything.

        Returns:
            str: Json string.
        '''
        return json.dumps(raw_data, cls=self._Encoder)

    def deserialize(self, serialized_data: str, dtos: list[type[BaseModel]] | None = None) -> Any:
        '''Wrapper for deserialization.

        Args:
            serialized_data (str): Json string.
            dtos (list[type[BaseModel]] | None): Pydantic models to deserialize.

        Returns:
            Any: Deserialized data.
        '''
        if dtos:
            return json.loads(serialized_data, object_hook=self._Decoder.from_dict(dtos))
        else:
            return json.loads(serialized_data)
