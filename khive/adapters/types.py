from .adapter import Adaptable, Adapter, AdapterRegistry
from .json_adapter import JsonAdapter, JsonFileAdapter
from .pd_dataframe_adapter import PandasDataFrameAdapter
from .toml_adapter import TomlAdapter, TomlFileAdapter
from .validation import validate_data


class PileAdapterRegistry(AdapterRegistry):
    pass


DEFAULT_PILE_ADAPTERS = (
    JsonAdapter,
    JsonFileAdapter,
    TomlAdapter,
    TomlFileAdapter,
    PandasDataFrameAdapter,
)


class NodeAdapterRegistry(AdapterRegistry):
    pass


DEFAULT_NODE_ADAPTERS = (
    JsonAdapter,
    JsonFileAdapter,
    TomlAdapter,
    TomlFileAdapter,
)

for i in DEFAULT_PILE_ADAPTERS:
    PileAdapterRegistry.register(i)

for i in DEFAULT_NODE_ADAPTERS:
    NodeAdapterRegistry.register(i)


__all__ = (
    "Adapter",
    "AdapterRegistry",
    "JsonAdapter",
    "JsonFileAdapter",
    "TomlAdapter",
    "TomlFileAdapter",
    "PandasDataFrameAdapter",
    "Adaptable",
    "PileAdapterRegistry",
    "NodeAdapterRegistry",
    "validate_data",
)
