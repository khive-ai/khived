import importlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

from typing_extensions import get_protocol_members

from khive._errors import MissingAdapterError

T = TypeVar("T")

__all__ = (
    "Adapter",
    "ADAPTER_MEMBERS",
    "AdapterRegistry",
)


@runtime_checkable
class Adapter(Protocol):
    """
    Describes a two-way converter that knows how to transform an object
    from an external representation to an internal format, and vice versa.

    Attributes
    ----------
    obj_key : str
        A unique key or extension that identifies what format this
        adapter supports (e.g. ".csv", "json", "pd_dataframe").
        conventions:
            - local file should use keys like `.csv`, `.json`, `.toml`, ...
            - filepath must use `fp` keyword parameter
            - integration should be like, `pd_dataframe`, `mongodb_document`, `neo4j_node`

    Methods
    -------
    from_obj(subj_cls: type[T], obj: Any, /, many: bool, **kwargs) -> dict|list[dict]
        Converts a raw external object (file contents, JSON string, etc.)
        into a dictionary or list of dictionaries.
    to_obj(subj: T, /, many: bool, **kwargs) -> Any
        Converts an internal object (e.g., a Pydantic-based model)
        into the target format (file, JSON, DataFrame, etc.).
    """

    obj_key: str

    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: Any,
        /,
        *,
        many: bool,
        **kwargs,
    ) -> dict | list[dict]:
        """many should return a list"""

    @classmethod
    def to_obj(
        cls,
        subj: T,
        /,
        *,
        many: bool,
        **kwargs,
    ) -> Any:
        """
        many should return a list
        """


ADAPTER_MEMBERS = get_protocol_members(Adapter)  # duck typing


class AdapterRegistry:
    """
    Registry for adapter classes that handle conversion between different formats.

    This registry maps object keys (like file extensions or format identifiers) to
    adapter implementations. It supports both runtime registration and loading from
    a pre-computed registry file for improved performance.
    """

    _adapters: dict[str, Adapter] = {}
    _adapter_map: dict[str, str] = {}
    _initialized: bool = False
    _registry_load_time: float | None = None

    @classmethod
    def _initialize(cls) -> None:
        """
        Initialize the registry by loading the pre-computed adapter map if available.
        This is called lazily when needed to avoid unnecessary filesystem operations
        during import time.
        """
        if cls._initialized:
            return

        # Try to load the pre-computed adapter map
        start_time = time.time()
        cls._load_adapter_map()
        cls._initialized = True
        cls._registry_load_time = time.time() - start_time

        if cls._registry_load_time > 0.3:  # 300ms threshold
            logging.warning(
                f"AdapterRegistry initialization took {cls._registry_load_time:.3f}s. "
                "Consider running 'lionagi build-registry' to improve startup performance."
            )

    @classmethod
    def _load_adapter_map(cls) -> None:
        """
        Load the pre-computed adapter map from the JSON file if it exists.
        """
        # Determine the package directory
        package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        adapter_map_path = os.path.join(package_dir, "adapter_map.json")

        if os.path.exists(adapter_map_path):
            try:
                with open(adapter_map_path, "r", encoding="utf-8") as f:
                    cls._adapter_map = json.load(f)
                logging.debug(
                    f"Loaded adapter map from {adapter_map_path} with {len(cls._adapter_map)} entries"
                )
            except Exception as e:
                logging.warning(
                    f"Error loading adapter map from {adapter_map_path}: {e}"
                )
        else:
            logging.debug(f"Adapter map not found at {adapter_map_path}")

    @classmethod
    def _import_adapter(cls, obj_key: str) -> Adapter | None:
        """
        Import and register an adapter from the pre-computed map.

        Args:
            obj_key: The object key to import the adapter for
        """
        if not cls._initialized:
            cls._initialize()

        if obj_key not in cls._adapter_map:
            return None

        module_path = cls._adapter_map[obj_key]
        try:
            # Split the module path into module and class name
            module_name, class_name = module_path.rsplit(".", 1)

            # Import the module
            module = importlib.import_module(module_name)

            # Get the adapter class
            adapter_class = getattr(module, class_name)

            # Register the adapter
            cls.register(adapter_class)

            # Return the registered adapter
            return cls._adapters[obj_key]
        except Exception as e:
            logging.warning(
                f"Error importing adapter for {obj_key} from {module_path}: {e}"
            )
            return None

    @classmethod
    def list_adapters(cls) -> list[tuple[str | type, ...]]:
        """List all registered adapters."""
        if not cls._initialized:
            cls._initialize()
        return list(cls._adapters.keys())

    @classmethod
    def register(cls, adapter: type[Adapter]) -> None:
        """Register an adapter with the registry."""
        for member in ADAPTER_MEMBERS:
            if not hasattr(adapter, member):
                _str = getattr(adapter, "obj_key", None) or repr(adapter)
                _str = _str[:50] if len(_str) > 50 else _str
                raise AttributeError(f"Adapter {_str} missing required methods.")

        if isinstance(adapter, type):
            cls._adapters[adapter.obj_key] = adapter()
        else:
            cls._adapters[adapter.obj_key] = adapter

    @classmethod
    def get(cls, obj_key: type | str) -> Adapter:
        """
        Get an adapter by its object key.

        This method first checks if the adapter is already registered. If not, it attempts
        to import it from the pre-computed map. If that fails, it raises MissingAdapterError.

        Args:
            obj_key: The object key to get the adapter for
        """
        if not cls._initialized:
            cls._initialize()

        try:
            # First, check if the adapter is already registered
            return cls._adapters[obj_key]
        except KeyError:
            # If not, try to import it from the pre-computed map
            adapter = cls._import_adapter(obj_key)
            if adapter is not None:
                return adapter

            # If all else fails, raise MissingAdapterError
            logging.error(f"Error getting adapter for {obj_key}. Adapter not found.")
            raise MissingAdapterError(f"Adapter for key '{obj_key}' not found")
        except Exception as e:
            logging.error(f"Error getting adapter for {obj_key}. Error: {e}")
            raise

    @classmethod
    def adapt_from(
        cls, subj_cls: type[T], obj: Any, obj_key: type | str, **kwargs
    ) -> dict | list[dict]:
        try:
            return cls.get(obj_key).from_obj(subj_cls, obj, **kwargs)
        except MissingAdapterError:
            logging.error(f"Error adapting data from {obj_key}. Adapter not found.")
            raise
        except Exception as e:
            logging.error(f"Error adapting data from {obj_key}. Error: {e}")
            raise

    @classmethod
    def adapt_to(cls, subj: T, obj_key: type | str, **kwargs) -> Any:
        try:
            return cls.get(obj_key).to_obj(subj, **kwargs)
        except MissingAdapterError:
            logging.error(f"Error adapting data to {obj_key}. Adapter not found.")
            raise
        except Exception as e:
            logging.error(f"Error adapting data to {obj_key}. Error: {e}")
            raise


class Adaptable(ABC):

    _adapter_registry: ClassVar[AdapterRegistry]

    @classmethod
    def register_adapter(cls, adapter: type[Adapter]):
        """Register new adapter."""
        cls._get_adapter_registry().register(adapter)

    @classmethod
    def list_adapters(cls):
        """List available adapters."""
        return cls._get_adapter_registry().list_adapters()

    @classmethod
    def _get_adapter_registry(cls) -> AdapterRegistry:
        if isinstance(cls._adapter_registry, type):
            cls._adapter_registry = cls._adapter_registry()
        return cls._adapter_registry

    @classmethod
    @abstractmethod
    def adapt_from(cls, obj: Any, obj_key: str, many: bool = False, **kwargs: Any):
        """Create from another format."""

    def adapt_to(self, obj_key: str, many: bool = False, **kwargs: Any) -> Any:
        """Convert to another format."""
        return self._get_adapter_registry().adapt_to(
            subj=self, obj_key=obj_key, many=many, **kwargs
        )
