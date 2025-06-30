"""
Serialization and deserialization utilities for the Pythonium framework.

This module provides comprehensive serialization support for various formats
including JSON, YAML, MessagePack, and custom binary formats.
"""

import base64
import gzip
import json
import pickle
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
)

if TYPE_CHECKING:
    import orjson as orjson_module
else:
    orjson_module = None

try:
    import orjson

    HAS_ORJSON = True
except ImportError:
    orjson = None  # type: ignore
    HAS_ORJSON = False

from pythonium.common.exceptions import PythoniumError
from pythonium.common.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class SerializationError(PythoniumError):
    """Base exception for serialization operations."""

    pass


class DeserializationError(PythoniumError):
    """Base exception for deserialization operations."""

    pass


class UnsupportedFormatError(SerializationError):
    """Exception raised when format is not supported."""

    pass


class SerializationFormat(Enum):
    """Supported serialization formats."""

    JSON = "json"
    YAML = "yaml"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    BINARY = "binary"
    XML = "xml"


@dataclass
class SerializationOptions:
    """Options for serialization."""

    format: SerializationFormat = SerializationFormat.JSON
    compress: bool = False
    include_metadata: bool = True
    pretty_print: bool = False
    encoding: str = "utf-8"
    use_orjson: bool = True  # Use orjson for JSON when available
    custom_encoders: Dict[Type, Callable[[Any], Any]] = field(default_factory=dict)
    custom_decoders: Dict[str, Callable[[Any], Any]] = field(default_factory=dict)


class BaseSerializer(ABC, Generic[T]):
    """Abstract base class for serializers."""

    def __init__(self, options: Optional[SerializationOptions] = None):
        self.options = options or SerializationOptions()

    @abstractmethod
    def serialize(self, obj: T) -> bytes:
        """Serialize object to bytes."""
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> T:
        """Deserialize bytes to object."""
        pass

    def serialize_to_string(self, obj: T) -> str:
        """Serialize object to string."""
        data = self.serialize(obj)
        return data.decode(self.options.encoding)

    def deserialize_from_string(self, data: str) -> T:
        """Deserialize string to object."""
        return self.deserialize(data.encode(self.options.encoding))

    def _compress_data(self, data: bytes) -> bytes:
        """Compress data if compression is enabled."""
        if self.options.compress:
            return gzip.compress(data)
        return data

    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data if it was compressed."""
        if self.options.compress:
            try:
                return gzip.decompress(data)
            except gzip.BadGzipFile:
                # Data might not be compressed
                return data
        return data


class JSONSerializer(BaseSerializer[Any]):
    """JSON serializer with support for custom types and orjson performance optimization."""

    def __init__(self, options: Optional[SerializationOptions] = None):
        super().__init__(options)
        self.use_orjson = HAS_ORJSON and getattr(self.options, "use_orjson", True)

        self._default_encoders = {
            datetime: lambda dt: {"__datetime__": dt.isoformat()},
            date: lambda d: {"__date__": d.isoformat()},
            time: lambda t: {"__time__": t.isoformat()},
            timedelta: lambda td: {"__timedelta__": td.total_seconds()},
            Decimal: lambda d: {"__decimal__": str(d)},
            set: lambda s: {"__set__": list(s)},
            frozenset: lambda fs: {"__frozenset__": list(fs)},
            bytes: lambda b: {"__bytes__": base64.b64encode(b).decode("ascii")},
            uuid.UUID: lambda u: {"__uuid__": str(u)},
            Path: lambda p: {"__path__": str(p)},
        }

        self._default_decoders = {
            "__datetime__": lambda s: datetime.fromisoformat(s),
            "__date__": lambda s: date.fromisoformat(s),
            "__time__": lambda s: time.fromisoformat(s),
            "__timedelta__": lambda s: timedelta(seconds=s),
            "__decimal__": lambda s: Decimal(s),
            "__set__": lambda items: set(items),
            "__frozenset__": lambda items: frozenset(items),
            "__bytes__": lambda s: base64.b64decode(s.encode("ascii")),
            "__uuid__": lambda s: uuid.UUID(s),
            "__path__": lambda s: Path(s),
        }

    def serialize(self, obj: Any) -> bytes:
        """Serialize object to JSON bytes using orjson when available for better performance."""
        try:
            # Prepare object for serialization
            serializable_obj = self._make_serializable(obj)

            # Add metadata if requested
            if self.options.include_metadata:
                wrapper = {
                    "data": serializable_obj,
                    "metadata": {
                        "serialized_at": datetime.utcnow().isoformat(),
                        "format": self.options.format.value,
                        "version": "1.0",
                    },
                }
            else:
                wrapper = serializable_obj

            # Serialize to JSON using orjson or standard json
            if self.use_orjson:
                # Use orjson for better performance
                orjson_options = 0
                if self.options.pretty_print:
                    orjson_options |= orjson.OPT_INDENT_2

                # orjson returns bytes directly
                data = orjson.dumps(wrapper, option=orjson_options)
            else:
                # Fallback to standard json
                json_kwargs: Dict[str, Any] = {}
                if self.options.pretty_print:
                    json_kwargs.update({"indent": 2, "sort_keys": True})

                json_str = json.dumps(wrapper, **json_kwargs)
                data = json_str.encode(self.options.encoding)

            return self._compress_data(data)

        except Exception as e:
            raise SerializationError(f"Failed to serialize to JSON: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        """Deserialize JSON bytes to object using orjson when available for better performance."""
        try:
            # Decompress if needed
            data = self._decompress_data(data)

            # Parse JSON using orjson or standard json
            if self.use_orjson:
                # orjson can handle bytes directly
                obj = orjson.loads(data)
            else:
                # Standard json needs string
                json_str = data.decode(self.options.encoding)
                obj = json.loads(json_str)

            # Extract data if metadata wrapper exists
            if isinstance(obj, dict) and "data" in obj and "metadata" in obj:
                obj = obj["data"]

            # Restore custom types
            return self._restore_types(obj)

        except Exception as e:
            raise DeserializationError(f"Failed to deserialize from JSON: {e}") from e

    def _make_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        # Handle custom encoders
        obj_type = type(obj)
        if obj_type in self.options.custom_encoders:
            return self.options.custom_encoders[obj_type](obj)

        # Handle default encoders
        if obj_type in self._default_encoders:
            return self._default_encoders[obj_type](obj)

        # Handle dataclasses
        if is_dataclass(obj) and not isinstance(obj, type):
            return {
                "__dataclass__": {
                    "module": obj.__class__.__module__,
                    "name": obj.__class__.__name__,
                    "data": asdict(obj),
                }
            }

        # Handle enums
        if isinstance(obj, Enum):
            return {
                "__enum__": {
                    "module": obj.__class__.__module__,
                    "name": obj.__class__.__name__,
                    "value": obj.value,
                }
            }

        # Handle collections recursively
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            result = [self._make_serializable(item) for item in obj]
            if isinstance(obj, tuple):
                return {"__tuple__": result}
            return result

        # Return as-is for JSON-serializable types
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj

        # Fallback to string representation
        logger.warning(f"Converting non-serializable object {type(obj)} to string")
        return {"__string__": str(obj)}

    def _restore_types(self, obj: Any) -> Any:
        """Restore custom types from JSON data."""
        if isinstance(obj, dict):
            # Check for type markers
            if len(obj) == 1:
                key, value = next(iter(obj.items()))

                # Handle custom decoders
                if key in self.options.custom_decoders:
                    return self.options.custom_decoders[key](value)

                # Handle default decoders
                if key in self._default_decoders:
                    return self._default_decoders[key](value)

                # Handle special types
                if key == "__tuple__":
                    return tuple(self._restore_types(item) for item in value)
                elif key == "__dataclass__":
                    return self._restore_dataclass(value)
                elif key == "__enum__":
                    return self._restore_enum(value)
                elif key == "__string__":
                    return value

            # Recursively restore dict values
            return {k: self._restore_types(v) for k, v in obj.items()}

        elif isinstance(obj, list):
            return [self._restore_types(item) for item in obj]

        return obj

    def _restore_dataclass(self, data: Dict[str, Any]) -> Any:
        """Restore dataclass from serialized data."""
        try:
            module_name = data["module"]
            class_name = data["name"]
            field_data = data["data"]

            # Import the module and get the class
            import importlib

            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)

            # Restore field values
            restored_data = self._restore_types(field_data)

            return cls(**restored_data)
        except Exception as e:
            logger.warning(f"Failed to restore dataclass: {e}")
            return data

    def _restore_enum(self, data: Dict[str, Any]) -> Any:
        """Restore enum from serialized data."""
        try:
            module_name = data["module"]
            class_name = data["name"]
            value = data["value"]

            # Import the module and get the enum class
            import importlib

            module = importlib.import_module(module_name)
            enum_cls = getattr(module, class_name)

            return enum_cls(value)
        except Exception as e:
            logger.warning(f"Failed to restore enum: {e}")
            return data


class PickleSerializer(BaseSerializer[Any]):
    """Pickle serializer for Python objects."""

    def serialize(self, obj: Any) -> bytes:
        """Serialize object using pickle."""
        try:
            data = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
            return self._compress_data(data)
        except Exception as e:
            raise SerializationError(f"Failed to serialize with pickle: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        """Deserialize object using pickle."""
        try:
            data = self._decompress_data(data)
            return pickle.loads(data)
        except Exception as e:
            raise DeserializationError(f"Failed to deserialize with pickle: {e}") from e


class YAMLSerializer(BaseSerializer[Any]):
    """YAML serializer (requires PyYAML)."""

    def __init__(self, options: Optional[SerializationOptions] = None):
        super().__init__(options)
        try:
            import yaml

            self.yaml = yaml
        except ImportError as e:
            raise UnsupportedFormatError(
                "PyYAML is required for YAML serialization"
            ) from e

    def serialize(self, obj: Any) -> bytes:
        """Serialize object to YAML bytes."""
        try:
            # Convert to JSON-serializable format first
            json_serializer = JSONSerializer(self.options)
            serializable_obj = json_serializer._make_serializable(obj)

            yaml_str = self.yaml.dump(
                serializable_obj,
                default_flow_style=not self.options.pretty_print,
            )
            data = yaml_str.encode(self.options.encoding)

            return self._compress_data(data)
        except Exception as e:
            raise SerializationError(f"Failed to serialize to YAML: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        """Deserialize YAML bytes to object."""
        try:
            data = self._decompress_data(data)
            yaml_str = data.decode(self.options.encoding)
            obj = self.yaml.safe_load(yaml_str)

            # Restore types using JSON deserializer
            json_serializer = JSONSerializer(self.options)
            return json_serializer._restore_types(obj)
        except Exception as e:
            raise DeserializationError(f"Failed to deserialize from YAML: {e}") from e


class SerializerFactory:
    """Factory for creating serializers."""

    _serializers = {
        SerializationFormat.JSON: JSONSerializer,
        SerializationFormat.PICKLE: PickleSerializer,
        SerializationFormat.YAML: YAMLSerializer,
    }

    @classmethod
    def create(
        self,
        format: SerializationFormat,
        options: Optional[SerializationOptions] = None,
    ) -> BaseSerializer:
        """Create a serializer for the specified format."""
        if format not in self._serializers:
            raise UnsupportedFormatError(f"Unsupported format: {format}")

        serializer_class = self._serializers[format]
        # The serializer_class is guaranteed to be a concrete implementation
        return serializer_class(options)  # type: ignore

    @classmethod
    def register_serializer(
        self,
        format: SerializationFormat,
        serializer_class: Type[BaseSerializer],
    ) -> None:
        """Register a custom serializer."""
        self._serializers[format] = serializer_class


def serialize(
    obj: Any, format: SerializationFormat = SerializationFormat.JSON, **kwargs
) -> bytes:
    """Serialize an object using the specified format."""
    options = SerializationOptions(format=format, **kwargs)
    serializer = SerializerFactory.create(format, options)
    return serializer.serialize(obj)


def deserialize(
    data: bytes,
    format: SerializationFormat = SerializationFormat.JSON,
    **kwargs,
) -> Any:
    """Deserialize data using the specified format."""
    options = SerializationOptions(format=format, **kwargs)
    serializer = SerializerFactory.create(format, options)
    return serializer.deserialize(data)


def serialize_to_string(
    obj: Any, format: SerializationFormat = SerializationFormat.JSON, **kwargs
) -> str:
    """Serialize an object to string."""
    options = SerializationOptions(format=format, **kwargs)
    serializer = SerializerFactory.create(format, options)
    return serializer.serialize_to_string(obj)


def deserialize_from_string(
    data: str, format: SerializationFormat = SerializationFormat.JSON, **kwargs
) -> Any:
    """Deserialize string data."""
    options = SerializationOptions(format=format, **kwargs)
    serializer = SerializerFactory.create(format, options)
    return serializer.deserialize_from_string(data)


def serialize_to_file(
    obj: Any,
    file_path: Union[str, Path],
    format: Optional[SerializationFormat] = None,
    **kwargs,
) -> None:
    """Serialize an object to a file."""
    file_path = Path(file_path)

    # Auto-detect format from file extension if not specified
    if format is None:
        ext = file_path.suffix.lower()
        if ext == ".json":
            format = SerializationFormat.JSON
        elif ext in [".yml", ".yaml"]:
            format = SerializationFormat.YAML
        elif ext == ".pkl":
            format = SerializationFormat.PICKLE
        else:
            format = SerializationFormat.JSON

    options = SerializationOptions(format=format, **kwargs)
    serializer = SerializerFactory.create(format, options)

    data = serializer.serialize(obj)
    file_path.write_bytes(data)


def deserialize_from_file(
    file_path: Union[str, Path],
    format: Optional[SerializationFormat] = None,
    **kwargs,
) -> Any:
    """Deserialize an object from a file."""
    file_path = Path(file_path)

    # Auto-detect format from file extension if not specified
    if format is None:
        ext = file_path.suffix.lower()
        if ext == ".json":
            format = SerializationFormat.JSON
        elif ext in [".yml", ".yaml"]:
            format = SerializationFormat.YAML
        elif ext == ".pkl":
            format = SerializationFormat.PICKLE
        else:
            format = SerializationFormat.JSON

    options = SerializationOptions(format=format, **kwargs)
    serializer = SerializerFactory.create(format, options)

    data = file_path.read_bytes()
    return serializer.deserialize(data)


# JSON-specific convenience functions
def to_json(obj: Any, pretty: bool = False, **kwargs) -> str:
    """Serialize an object to JSON string with common options."""
    return serialize_to_string(
        obj, format=SerializationFormat.JSON, pretty_print=pretty, **kwargs
    )


def from_json(data: str, **kwargs) -> Any:
    """Deserialize JSON string to object."""
    return deserialize_from_string(data, format=SerializationFormat.JSON, **kwargs)


def to_json_bytes(obj: Any, pretty: bool = False, **kwargs) -> bytes:
    """Serialize an object to JSON bytes."""
    options = SerializationOptions(
        format=SerializationFormat.JSON, pretty_print=pretty, **kwargs
    )
    serializer = SerializerFactory.create(SerializationFormat.JSON, options)
    return serializer.serialize(obj)


def from_json_bytes(data: bytes, **kwargs) -> Any:
    """Deserialize JSON bytes to object."""
    options = SerializationOptions(format=SerializationFormat.JSON, **kwargs)
    serializer = SerializerFactory.create(SerializationFormat.JSON, options)
    return serializer.deserialize(data)
