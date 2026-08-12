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

    @staticmethod
    def _series_from_first_available_column(dataframe: pd.DataFrame, *column_names: str) -> pd.Series:
        """Returns the first matching column or an empty aligned Series."""
        for column_name in column_names:
            if column_name in dataframe.columns:
                selected = dataframe[column_name]
                # Duplicate column labels can return a DataFrame; keep first aligned column.
                if isinstance(selected, pd.DataFrame):
                    return selected.iloc[:, 0]
                return selected
        return pd.Series("", index=dataframe.index, dtype="object")

    def _ensure_normalized_customer_columns(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        """Ensures customer matching keys exist even when source columns vary."""
        normalized_customers_df = customers_df.copy()

        normalized_customers_df["customer_document_normalized"] = self._series_from_first_available_column(
            normalized_customers_df,
            "customer_document_normalized",
            "CNPJ/CPF",
            "CPF/CNPJ",
            "CPF/CNPJ do Cliente",
        ).apply(normalize_document)
        normalized_customers_df["customer_legal_name_normalized"] = self._series_from_first_available_column(
            normalized_customers_df,
            "customer_legal_name_normalized",
            "Razão Social",
            "Razao Social",
        ).apply(normalize_customer_name)
        normalized_customers_df["customer_name_normalized"] = self._series_from_first_available_column(
            normalized_customers_df,
            "customer_name_normalized",
            "Nome Fantasia",
            "Nome do Cliente",
            "Cliente",
        ).apply(normalize_customer_name)

        return normalized_customers_df

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

        normalized_customers_df = self._ensure_normalized_customer_columns(customers_df)

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

        customers_df = self._ensure_normalized_customer_columns(self.load_customers())
        if customers_df.empty:
            return sales_df.copy()

        customers_by_document_df = (
            customers_df.loc[customers_df["customer_document_normalized"].ne("")]
            .drop_duplicates(subset=["customer_document_normalized"], keep="first")
        )
        customers_by_legal_name_df = (
            customers_df.loc[customers_df["customer_legal_name_normalized"].ne("")]
            .drop_duplicates(subset=["customer_legal_name_normalized"], keep="first")
        )
        customers_by_name_df = (
            customers_df.loc[customers_df["customer_name_normalized"].ne("")]
            .drop_duplicates(subset=["customer_name_normalized"], keep="first")
        )

        enriched_sales_df = sales_df.copy()
        enriched_sales_df["customer_document_normalized"] = self._series_from_first_available_column(
            enriched_sales_df,
            "CPF/CNPJ do Cliente",
        ).apply(normalize_document)
        enriched_sales_df["customer_legal_name_normalized"] = self._series_from_first_available_column(
            enriched_sales_df,
            "Razão Social",
        ).apply(normalize_customer_name)
        enriched_sales_df["customer_name_normalized"] = self._series_from_first_available_column(
            enriched_sales_df,
            "Nome do Cliente",
            "Cliente",
        ).apply(normalize_customer_name)

        matched_sales_df = enriched_sales_df.merge(
            customers_by_document_df,
            on=["customer_document_normalized"],
            how="left",
            suffixes=("", "_master"),
        )

        missing_doc_mask = matched_sales_df["customer_document_normalized"].eq("")
        missing_match_mask = matched_sales_df.get(
            "customer_name_normalized_master",
            pd.Series("", index=matched_sales_df.index, dtype="object"),
        ).fillna("").eq("")
        fallback_by_legal_name_mask = missing_doc_mask | missing_match_mask

        if fallback_by_legal_name_mask.any():
            fallback_sales_df = matched_sales_df.loc[fallback_by_legal_name_mask].drop(
                columns=[col for col in matched_sales_df.columns if col.endswith("_master")],
                errors="ignore",
            )
            fallback_legal_name_df = fallback_sales_df.merge(
                customers_by_legal_name_df,
                on=["customer_legal_name_normalized"],
                how="left",
                suffixes=("", "_master"),
            )
            master_columns = [
                column
                for column in fallback_legal_name_df.columns
                if column not in fallback_sales_df.columns
            ]
            if master_columns:
                for column in master_columns:
                    if column not in matched_sales_df.columns:
                        matched_sales_df[column] = pd.NA
                    if pd.api.types.is_object_dtype(fallback_legal_name_df[column].dtype) and not pd.api.types.is_object_dtype(
                        matched_sales_df[column].dtype
                    ):
                        matched_sales_df[column] = matched_sales_df[column].astype("object")
                    matched_sales_df.loc[fallback_by_legal_name_mask, column] = fallback_legal_name_df[column].to_numpy()
            if "customer_legal_name_normalized_master" in matched_sales_df.columns:
                matched_sales_df.loc[
                    fallback_by_legal_name_mask,
                    "customer_legal_name_normalized_master",
                ] = fallback_legal_name_df["customer_legal_name_normalized"].to_numpy()

        remaining_missing_mask = matched_sales_df.get(
            "customer_name_normalized_master",
            pd.Series("", index=matched_sales_df.index, dtype="object"),
        ).fillna("").eq("")
        if remaining_missing_mask.any():
            fallback_name_base_df = matched_sales_df.loc[remaining_missing_mask].drop(
                columns=[col for col in matched_sales_df.columns if col.endswith("_master")],
                errors="ignore",
            )
            fallback_name_df = fallback_name_base_df.merge(
                customers_by_name_df,
                on=["customer_name_normalized"],
                how="left",
                suffixes=("", "_master"),
            )
            master_columns = [
                column
                for column in fallback_name_df.columns
                if column not in fallback_name_base_df.columns
            ]
            if master_columns:
                for column in master_columns:
                    if column not in matched_sales_df.columns:
                        matched_sales_df[column] = pd.NA
                    if pd.api.types.is_object_dtype(fallback_name_df[column].dtype) and not pd.api.types.is_object_dtype(
                        matched_sales_df[column].dtype
                    ):
                        matched_sales_df[column] = matched_sales_df[column].astype("object")
                    matched_sales_df.loc[remaining_missing_mask, column] = fallback_name_df[column].to_numpy()
            if "customer_name_normalized_master" in matched_sales_df.columns:
                matched_sales_df.loc[
                    remaining_missing_mask,
                    "customer_name_normalized_master",
                ] = fallback_name_df["customer_name_normalized"].to_numpy()

        return matched_sales_df
