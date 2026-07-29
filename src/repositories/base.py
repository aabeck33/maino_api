"""Base abstractions for repository components."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from utils.geo import read_excel_shared


class BaseRepository:
    """Base repository with in-memory DataFrame cache helpers."""

    def __init__(self) -> None:
        self._cache: dict[str, pd.DataFrame] = {}

    def clear_cache(self) -> None:
        """Clears all cached datasets."""
        self._cache.clear()

    def _read_excel(self, file_path: Path, **kwargs: object) -> pd.DataFrame:
        """Reads an Excel file using shared-read mode to avoid lock conflicts."""
        excel_buffer = read_excel_shared(file_path)
        return pd.read_excel(excel_buffer, engine="openpyxl", **kwargs)

    def _get_cached(self, key: str) -> pd.DataFrame | None:
        """Retrieves a cached DataFrame by key when available."""
        return self._cache.get(key)

    def _set_cached(self, key: str, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Stores a copy in cache and returns the cached value."""
        self._cache[key] = dataframe.copy()
        return self._cache[key]
