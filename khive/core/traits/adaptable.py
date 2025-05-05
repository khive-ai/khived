from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from khive.adapters.adapter import Adapter, AdapterRegistry


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
        pass

    def adapt_to(self, obj_key: str, many: bool = False, **kwargs: Any) -> Any:
        """Convert to another format."""
        return self._get_adapter_registry().adapt_to(
            subj=self, obj_key=obj_key, many=many, **kwargs
        )
