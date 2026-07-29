"""Repository for sales ingestion, cleaning and normalization."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from config.settings import SETTINGS
from repositories.base import BaseRepository
from repositories.normalization import normalize_invoice_status


class SalesRepository(BaseRepository):
    """Provides normalized sales rows and product code mapping support."""

    CACHE_KEY = "sales_orders"

    def load_sales_orders(self, file_path: Path | None = None) -> pd.DataFrame:
        """Loads and normalizes sales orders from Excel.

        Parameters
        ----------
        file_path : Path | None
            Optional override path for sales orders file.

        Returns
        -------
        pd.DataFrame
            Normalized sales dataset.
        """
        cached = self._get_cached(self.CACHE_KEY)
        if cached is not None:
            return cached.copy()

        source_path = file_path or SETTINGS.data_file_path(SETTINGS.data_files.sales_orders)
        if not source_path.exists():
            raise FileNotFoundError(f"Planilha de vendas não encontrada no caminho: {source_path}")

        sales_df = self._read_excel(source_path)
        normalized_sales_df = self.normalize_sales_schema(sales_df)

        return self._set_cached(self.CACHE_KEY, normalized_sales_df).copy()

    @staticmethod
    def normalize_sales_schema(sales_df: pd.DataFrame) -> pd.DataFrame:
        """Applies schema and dtype normalization for sales rows."""
        if sales_df.empty:
            return sales_df.copy()

        normalized_sales_df = sales_df.copy()
        normalized_sales_df["Quantidade"] = pd.to_numeric(normalized_sales_df.get("Quantidade", 0.0), errors="coerce").fillna(0.0)
        normalized_sales_df["Número do Pedido"] = normalized_sales_df.get("Número do Pedido", "").astype(str)
        normalized_sales_df["Código do Produto"] = normalized_sales_df.get("Código do Produto", "").astype(str).str.strip()
        normalized_sales_df["ID da Nota Fiscal"] = normalized_sales_df.get("ID da Nota Fiscal", "").astype(str).str.strip()
        normalized_sales_df["Status da Nota Fiscal"] = normalized_sales_df.get("Status da Nota Fiscal", "").astype(str).str.strip()
        normalized_sales_df["URL NFe"] = normalized_sales_df.get("URL NFe", "").astype(str).str.strip()
        normalized_sales_df["CEP"] = normalized_sales_df.get("CEP", "").astype(str).str.strip()
        normalized_sales_df["Representante"] = normalized_sales_df.get("Representante", "").astype(str).str.strip()

        if "UF" not in normalized_sales_df.columns:
            normalized_sales_df["UF"] = "N/A"
        normalized_sales_df["UF"] = normalized_sales_df["UF"].astype(str).str.strip().str.upper().replace({"": "N/A"})

        return normalized_sales_df

    def load_product_code_mapping(self, file_path: Path | None = None) -> dict[str, str]:
        """Loads old->new product code conversion from historical workbook."""
        mapping_path = file_path or SETTINGS.data_file_path(SETTINGS.data_files.history)
        if not mapping_path.exists():
            return {}

        mapping_df = self._read_excel(mapping_path, sheet_name="Códigos")
        if mapping_df.empty:
            return {}

        old_code_column = "Código Gerensys"
        new_code_column = "Código Maino"
        if old_code_column not in mapping_df.columns or new_code_column not in mapping_df.columns:
            return {}

        return dict(
            zip(
                mapping_df[old_code_column].astype(str).str.strip(),
                mapping_df[new_code_column].astype(str).str.strip(),
            )
        )

    def apply_product_code_mapping(self, sales_df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
        """Replaces product codes according to the historical mapping table."""
        if sales_df.empty or not mapping:
            return sales_df.copy()

        mapped_sales_df = sales_df.copy()
        mapped_sales_df["Código do Produto"] = mapped_sales_df["Código do Produto"].map(
            lambda code: mapping.get(str(code).strip(), str(code).strip())
        )
        return mapped_sales_df

    @staticmethod
    def is_non_emitted_invoice(status: str) -> bool:
        """Determines whether an invoice status should be treated as non-emitted."""
        normalized_status = normalize_invoice_status(status)
        return normalized_status in {"NAO_TRANSMITIDA", "NAO EMITIDA"}
