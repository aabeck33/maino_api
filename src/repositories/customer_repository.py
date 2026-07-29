"""Repository for customer master data and matching strategies."""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from config.settings import SETTINGS
from repositories.base import BaseRepository
from repositories.normalization import normalize_customer_name, normalize_document


class CustomerRepository(BaseRepository):
    """Loads customers master data and provides deterministic matching keys."""

    CACHE_KEY = "customers_catalog"

    def load_customers(self, file_path: Path | None = None) -> pd.DataFrame:
        """Loads and normalizes customers from the official customers source.

        Matching hierarchy support:
        1. CPF/CNPJ
        2. Razão Social
        3. Nome do Cliente

        Parameters
        ----------
        file_path : Path | None
            Optional override path for customers Excel.

        Returns
        -------
        pd.DataFrame
            Customers table with normalized fields.
        """
        cached = self._get_cached(self.CACHE_KEY)
        if cached is not None:
            return cached.copy()

        source_path = file_path or SETTINGS.data_file_path(SETTINGS.data_files.customers)
        if not source_path.exists():
            return pd.DataFrame(columns=[
                "customer_document_normalized",
                "customer_legal_name_normalized",
                "customer_name_normalized",
            ])

        customers_df = self._read_excel(source_path)
        if customers_df.empty:
            return pd.DataFrame(columns=[
                "customer_document_normalized",
                "customer_legal_name_normalized",
                "customer_name_normalized",
            ])

        normalized_customers_df = customers_df.copy()

        document_series = normalized_customers_df.get("CPF/CNPJ", normalized_customers_df.get("CPF/CNPJ do Cliente", ""))
        legal_name_series = normalized_customers_df.get("Razão Social", normalized_customers_df.get("Razao Social", ""))
        display_name_series = normalized_customers_df.get("Nome do Cliente", normalized_customers_df.get("Cliente", ""))

        normalized_customers_df["customer_document_normalized"] = document_series.apply(normalize_document)
        normalized_customers_df["customer_legal_name_normalized"] = legal_name_series.apply(normalize_customer_name)
        normalized_customers_df["customer_name_normalized"] = display_name_series.apply(normalize_customer_name)

        return self._set_cached(self.CACHE_KEY, normalized_customers_df).copy()

    def enrich_sales_with_customer_master(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        """Matches sales rows with customer master using prioritized matching strategy.

        Parameters
        ----------
        sales_df : pd.DataFrame
            Sales dataset with customer columns.

        Returns
        -------
        pd.DataFrame
            Sales dataframe enriched with customer master fields when available.
        """
        if sales_df.empty:
            return sales_df.copy()

        customers_df = self.load_customers()
        if customers_df.empty:
            return sales_df.copy()

        enriched_sales_df = sales_df.copy()
        enriched_sales_df["customer_document_normalized"] = enriched_sales_df.get("CPF/CNPJ do Cliente", "").apply(normalize_document)
        enriched_sales_df["customer_legal_name_normalized"] = enriched_sales_df.get("Razão Social", "").apply(normalize_customer_name)
        enriched_sales_df["customer_name_normalized"] = enriched_sales_df.get("Nome do Cliente", "").apply(normalize_customer_name)

        matched_sales_df = enriched_sales_df.merge(
            customers_df,
            on=["customer_document_normalized"],
            how="left",
            suffixes=("", "_master"),
        )

        missing_doc_mask = matched_sales_df["customer_document_normalized"].eq("")
        missing_match_mask = matched_sales_df.get("customer_name_normalized_master", pd.Series([""] * len(matched_sales_df))).eq("")
        fallback_by_legal_name_mask = missing_doc_mask | missing_match_mask

        if fallback_by_legal_name_mask.any():
            fallback_sales_df = matched_sales_df.loc[fallback_by_legal_name_mask].drop(
                columns=[col for col in matched_sales_df.columns if col.endswith("_master")],
                errors="ignore",
            )
            fallback_legal_name_df = fallback_sales_df.merge(
                customers_df,
                on=["customer_legal_name_normalized"],
                how="left",
                suffixes=("", "_master"),
            )
            matched_sales_df.loc[fallback_by_legal_name_mask, fallback_legal_name_df.columns] = fallback_legal_name_df.values

        remaining_missing_mask = matched_sales_df.get("customer_name_normalized_master", pd.Series([""] * len(matched_sales_df))).eq("")
        if remaining_missing_mask.any():
            fallback_name_df = matched_sales_df.loc[remaining_missing_mask].drop(
                columns=[col for col in matched_sales_df.columns if col.endswith("_master")],
                errors="ignore",
            )
            fallback_name_df = fallback_name_df.merge(
                customers_df,
                on=["customer_name_normalized"],
                how="left",
                suffixes=("", "_master"),
            )
            matched_sales_df.loc[remaining_missing_mask, fallback_name_df.columns] = fallback_name_df.values

        return matched_sales_df
