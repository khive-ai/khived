from .adapter import Adapter, T

_HAS_PANDAS = True
try:
    import pandas as pd  # type: ignore[import]
except ImportError:
    _HAS_PANDAS = False


class PandasDataFrameAdapter(Adapter):
    """
    Converts a set of objects to a single `pd.DataFrame`, or
    a DataFrame to a list of dictionaries. Typically used in memory,
    not for saving to file.
    """

    obj_key = "pd_dataframe"
    alias = ("pandas_dataframe", "pd.DataFrame", "pd_dataframe", "pandas")

    @classmethod
    def from_obj(
        cls,
        subj_cls: type[T],
        obj,
        /,
        *,
        many: bool = False,
        orient: str = "records",
        **kwargs,
    ) -> list[dict]:
        """
        Convert an existing DataFrame into a list of dicts.

        Parameters
        ----------
        subj_cls : type[T]
            The internal class to which we might parse.
        obj : pd.DataFrame
            The DataFrame to convert.
        many : bool, optional
            Not used for DataFrame conversion, included for API consistency.
        orient : str, optional
            Orientation for DataFrame.to_dict, defaults to "records".
        **kwargs
            Additional args for DataFrame.to_dict.

        Returns
        -------
        list[dict]
            Each row as a dictionary.
        """
        return obj.to_dict(orient=orient, **kwargs)

    @classmethod
    def to_obj(
        cls, subj: list[T], /, *, many: bool = True, orient: str = "records", **kwargs
    ):
        """
        Convert multiple items into a DataFrame, adjusting `created_at` to datetime.

        Parameters
        ----------
        subj : list[T]
            The items to convert. Each item must have `to_dict()`.
        **kwargs
            Additional arguments for `pd.DataFrame(...)`.

        Returns
        -------
        pd.DataFrame
            The resulting DataFrame.
        """
        if not _HAS_PANDAS:
            raise ModuleNotFoundError(
                "Package `pandas` is needed to adapt to pandas dataframe, please install via `pip install pandas`"
            )

        # Vectorized timestamp fix: convert before frame creation
        rows = [dict(item.to_dict(), created_at=item.created_at) for item in subj]
        df = pd.DataFrame(rows, **kwargs)

        # Convert created_at to datetime using vectorized operation with caching
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(
                df["created_at"], errors="coerce", cache=True
            )

        return df
