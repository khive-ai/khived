from pathlib import Path

# Prefer std-lib parser for read paths in Python 3.11+
try:
    import tomllib as toml_reader  # 3.11+
except ModuleNotFoundError:
    import toml as toml_reader

# Use third-party toml for writing
import toml as toml_writer

from .adapter import Adapter, T


class TomlAdapter(Adapter):
    """
    Adapter that converts to/from TOML **strings** in memory.
    Example usage: taking a Python dictionary and making TOML,
    or parsing TOML string to a dict.
    """

    obj_key = "toml"

    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str,
        /,
        *,
        many: bool = False,
        **kwargs,
    ) -> dict | list[dict]:
        """
        Convert a TOML string into a dict or list of dicts.

        Parameters
        ----------
        subj_cls : type[T]
            The target class for context (not always used).
        obj : str
            The TOML string.
        many : bool, optional
            If True, expects a TOML array of tables (returns list[dict]).
            Otherwise returns a single dict.
        **kwargs
            Extra arguments for toml.loads().
        """
        result: dict = toml_reader.loads(obj, **kwargs)

        if many:
            # Use a reserved key 'items' for collections instead of guessing
            if "items" in result and isinstance(result["items"], list):
                return result["items"]
            # Fallback to wrapping the result in a list
            return [result]

        return result

    @classmethod
    def to_obj(
        cls,
        subj: T,
        *,
        many: bool = False,
        **kwargs,
    ) -> str:
        """
        Convert an object (or collection) to a TOML string.

        Parameters
        ----------
        subj : T
            The object to serialize.
        many : bool, optional
            If True, convert multiple items to a TOML array of tables.
        **kwargs
            Extra arguments for toml.dumps().
        """
        if many:
            if isinstance(subj, list):
                # Handle list of objects
                data = {"items": [item.to_dict() for item in subj]}
            elif hasattr(type(subj), "AsyncPileIterator"):
                # For multiple items, create a wrapper dict with an array of items
                data = {"items": [i.to_dict() for i in subj]}
            else:
                data = {"items": [subj.to_dict()]}
            return toml_writer.dumps(data, **kwargs)

        return toml_writer.dumps(subj.to_dict(), **kwargs)


class TomlFileAdapter(Adapter):
    """
    Adapter that reads/writes TOML data to/from a file on disk.
    The file extension key is ".toml".
    """

    obj_key = ".toml"

    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj: str | Path,
        /,
        *,
        many: bool = False,
        **kwargs,
    ) -> dict | list[dict]:
        """
        Read a TOML file from disk and return a dict or list of dicts.

        Parameters
        ----------
        subj_cls : type[T]
            The target class for context.
        obj : str | Path
            The TOML file path.
        many : bool
            If True, expects an array of tables. Otherwise single dict.
        **kwargs
            Extra arguments for toml.load().

        Returns
        -------
        dict | list[dict]
            The loaded data from file.
        """
        # tomllib requires binary mode
        with open(obj, "rb") as f:
            result = toml_reader.load(f, **kwargs)

        # Handle array of tables in TOML for "many" case
        if many:
            # Use a reserved key 'items' for collections instead of guessing
            if "items" in result and isinstance(result["items"], list):
                return result["items"]
            # Fallback to wrapping the result in a list
            return [result]

        return result

    @classmethod
    def to_obj(
        cls,
        subj: T,
        /,
        *,
        fp: str | Path,
        many: bool = False,
        mode: str = "w",
        **kwargs,
    ) -> None:
        """
        Write a dict (or list) to a TOML file.

        Parameters
        ----------
        subj : T
            The object/collection to serialize.
        fp : str | Path
            The file path to write.
        many : bool
            If True, write as a TOML array of tables of multiple items.
        mode : str
            File open mode, defaults to write ("w").
        **kwargs
            Extra arguments for toml.dump().

        Returns
        -------
        None
        """
        # Fail early on binary mode
        assert (
            isinstance(mode, str) and "b" not in mode
        ), "Binary mode not supported for TOML writing"

        with open(fp, mode, encoding="utf-8") as f:
            if many:
                if isinstance(subj, list):
                    # Handle list of objects
                    data = {"items": [item.to_dict() for item in subj]}
                elif hasattr(type(subj), "AsyncPileIterator"):
                    # TOML requires arrays of tables to be in a table
                    data = {"items": [i.to_dict() for i in subj]}
                else:
                    data = {"items": [subj.to_dict()]}
                toml_writer.dump(data, f, **kwargs)
            else:
                toml_writer.dump(subj.to_dict(), f, **kwargs)


# File: lionagi/protocols/adapters/toml_adapter.py
