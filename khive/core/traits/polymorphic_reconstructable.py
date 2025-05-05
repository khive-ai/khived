from __future__ import annotations

from abc import ABC

from .identifiable import Identifiable


class PolymorphicReconstructable(ABC):

    @classmethod
    def from_dict(cls: type[Identifiable], data: dict) -> Identifiable:
        """Deserializes a json dictionary into an Element or subclass of Element.

        If `lion_class` in `metadata` refers to a subclass, this method
        attempts to create an instance of that subclass."""

        from khive.utils import import_module

        from .._class_registry import get_class

        subcls: None | str = data.get("metadata", {}).get("lion_class")
        if subcls is not None and subcls != cls.class_name(True):
            try:
                subcls_type: type[Identifiable] = get_class(subcls.split(".")[-1])
            except Exception:
                try:
                    mod, imp = subcls.rsplit(".", 1)
                    subcls_type = import_module(mod, import_name=imp)
                except Exception:
                    pass

            if (
                hasattr(subcls_type, "from_dict")
                and subcls_type.from_dict.__func__ != cls.from_dict.__func__
            ):
                return subcls_type.from_dict(data)
        return cls.model_validate(data)
