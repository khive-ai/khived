from __future__ import annotations

from abc import ABC

from .identifiable import Identifiable


class NotReconstructable(ABC):
    """A class that cannot be reconstructed from a dictionary.

    This is used for classes that are not meant to be
    reconstructed from a dictionary, such as events.
    """

    @classmethod
    def from_dict(cls, data: dict) -> Identifiable:
        """Raises an error if called."""
        raise NotImplementedError(
            f"{cls.__name__} cannot be reconstructed from a dictionary."
        )
