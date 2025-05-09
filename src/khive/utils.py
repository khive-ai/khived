from typing import TypeVar

Import = TypeVar("I")

HasLen = TypeVar("HasLen")
Bin = list[int]

__all__ = ("get_bins", "import_module", "sha256_of_dict")


def import_module(
    package_name: str,
    module_name: str | None = None,
    import_name: str | list | None = None,
) -> Import | list[Import]:
    """Import a module by its path."""
    try:
        full_import_path = (
            f"{package_name}.{module_name}" if module_name else package_name
        )

        if import_name:
            import_name = (
                [import_name] if not isinstance(import_name, list) else import_name
            )
            a = __import__(
                full_import_path,
                fromlist=import_name,
            )
            if len(import_name) == 1:
                return getattr(a, import_name[0])
            return [getattr(a, name) for name in import_name]
        return __import__(full_import_path)

    except ImportError as e:
        error_msg = f"Failed to import module {full_import_path}: {e}"
        raise ImportError(error_msg) from e


def get_bins(input_: list[HasLen], /, upper: int) -> list[Bin]:
    """Organizes indices of items into bins based on a cumulative upper limit length.

    Args:
        input_ (list[str]): The list of strings to be binned.
        upper (int): The cumulative length upper limit for each bin.

    Returns:
        list[list[int]]: A list of bins, each bin is a list of indices from the input list.
    """
    current = 0
    bins = []
    current_bin = []
    for idx, item in enumerate(input_):
        if current + len(item) < upper:
            current_bin.append(idx)
            current += len(item)
        else:
            bins.append(current_bin)
            current_bin = [idx]
            current = len(item)
    if current_bin:
        bins.append(current_bin)
    return bins


def sha256_of_dict(obj: dict) -> str:
    """Deterministic SHA-256 of an arbitrary mapping."""
    import hashlib

    import orjson

    payload: bytes = orjson.dumps(
        obj,
        option=(
            orjson.OPT_SORT_KEYS  # canonical ordering
            | orjson.OPT_NON_STR_KEYS  # allow int / enum keys if you need them
        ),
    )
    return hashlib.sha256(memoryview(payload)).hexdigest()
