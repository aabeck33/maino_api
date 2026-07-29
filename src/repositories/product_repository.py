"""Repository responsible for products catalog ingestion and normalization."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from config.settings import SETTINGS
from repositories.base import BaseRepository


class ProductRepository(BaseRepository):
    """Provides normalized product catalog data."""

    CACHE_KEY = "products_catalog"

    def load_catalog(self, file_path: Path | None = None) -> pd.DataFrame:
        """Loads and normalizes products data from the configured source.

        Parameters
        ----------
        file_path : Path | None
            Optional override path for products Excel file.

        Returns
        -------
        pd.DataFrame
            Product catalog with normalized schema.
        """
        cached = self._get_cached(self.CACHE_KEY)
        if cached is not None:
            return cached.copy()

        source_path = file_path or SETTINGS.data_file_path(SETTINGS.data_files.products)
        if not source_path.exists():
            return pd.DataFrame(columns=["Código", "Descrição", "PU de entrada", "PU de saída", "Origem"])

        products_df = self._read_excel(source_path)
        if products_df.empty:
            return pd.DataFrame(columns=["Código", "Descrição", "PU de entrada", "PU de saída", "Origem"])

        normalized_products_df = products_df.copy()
        normalized_products_df["Código"] = normalized_products_df["Código"].astype(str).str.strip().str.upper()
        normalized_products_df["Descrição"] = normalized_products_df.get("Descrição", pd.Series(["N/A"] * len(normalized_products_df))).astype(str)
        normalized_products_df["Origem"] = normalized_products_df.get("Origem", pd.Series([""] * len(normalized_products_df))).astype(str)

        for price_column in ["PU de entrada", "PU de saída"]:
            normalized_products_df[price_column] = pd.to_numeric(
                normalized_products_df.get(price_column, 0.0),
                errors="coerce",
            ).fillna(0.0)

        return self._set_cached(self.CACHE_KEY, normalized_products_df).copy()
