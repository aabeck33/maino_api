"""Compatibility analytics facade built on top of repository and KPI layers."""

from __future__ import annotations

import os
import unicodedata
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from dotenv import load_dotenv

from analytics.kpis import (
    build_abc_analysis,
    build_abc_pareto_analysis,
    build_profitability_dataset,
    build_representative_monthly_evolution,
    calculate_clients_by_state,
    calculate_core_sales_kpis,
    calculate_financial_kpis,
    calculate_fiscal_distribution,
    calculate_order_stats,
    calculate_representative_performance,
    calculate_revenue_by_city,
    calculate_state_geo_coordinates,
    calculate_state_revenue,
    calculate_state_ticket_average,
    summarize_customers,
    summarize_monthly_profitability,
    summarize_profitability_by_customer,
    summarize_profitability_by_product,
    summarize_profitability_by_representative,
    summarize_representative_sales,
    top_cities_by_customers,
    top_cities_by_revenue,
)
from config.settings import SETTINGS
from repositories.customer_repository import CustomerRepository
from repositories.product_repository import ProductRepository
from repositories.sales_repository import SalesRepository
from utils.logger import setup_logger

logger = setup_logger("maino_analytics")
load_dotenv()

MIN_PED_TICKET_MEDIO = int(os.getenv("MIN_PED_TICKET_MEDIO", "1"))
LUCRO_OPERACIONAL_CUSTO_FIXO = float(os.getenv("LUCRO_OPERACIONAL_CUSTO_FIXO", "25"))
PROJECT_ROOT = SETTINGS.paths.project_root
WORK_DIR = SETTINGS.paths.work_dir


class SalesAnalytics:
    """Facade preserving the legacy public API while using the new architecture.

    Parameters
    ----------
    excel_path : Path
        Path to consolidated sales orders workbook.
    products_excel_path : Optional[Path]
        Optional products catalog workbook path.
    """

    def __init__(self, excel_path: Path, products_excel_path: Optional[Path] = None):
        self.excel_path = Path(excel_path)
        self.products_excel_path = Path(products_excel_path) if products_excel_path else None

        self.sales_repository = SalesRepository()
        self.product_repository = ProductRepository()
        self.customer_repository = CustomerRepository()

        self.products_df = self.load_products_catalog(self.products_excel_path)
        self.df = self._load_data()

    @classmethod
    def load_products_catalog(cls, products_excel_path: Optional[Path] = None) -> pd.DataFrame:
        """Loads product catalog with normalized prices and origin fields."""
        repository = ProductRepository()
        return repository.load_catalog(products_excel_path)

    @staticmethod
    def _coerce_customer_key(df: pd.DataFrame) -> pd.Series:
        """Builds a customer key from available columns."""
        if df.empty:
            return pd.Series(dtype="object")
        if "Cliente" in df.columns:
            raw_values = df["Cliente"]
        elif "Nome do Cliente" in df.columns:
            raw_values = df["Nome do Cliente"]
        elif "CPF/CNPJ do Cliente" in df.columns:
            raw_values = df["CPF/CNPJ do Cliente"]
        elif "Pedido ID" in df.columns:
            raw_values = df["Pedido ID"]
        else:
            raw_values = pd.Series(["N/A"] * len(df), index=df.index)

        return raw_values.astype(str).str.strip().replace({"": "N/A"}).fillna("N/A")

    def _load_data(self) -> pd.DataFrame:
        """Loads sales rows and applies centralized mapping and enrichment."""
        sales_df = self.sales_repository.load_sales_orders(self.excel_path)
        code_mapping = self.load_product_code_mapping()
        mapped_sales_df = self.sales_repository.apply_product_code_mapping(sales_df, code_mapping)

        try:
            enriched_sales_df = self.customer_repository.enrich_sales_with_customer_master(mapped_sales_df)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Falha ao enriquecer com base de clientes: %s", exc)
            enriched_sales_df = mapped_sales_df

        return enriched_sales_df

    @staticmethod
    def _normalize_status(status: Any) -> str:
        """Normalizes fiscal status values for filtering compatibility."""
        if status is None:
            return ""
        text = str(status).strip().upper()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return text

    def get_filtered_data(
        self,
        status_filter: str = "Todos",
        search_product: str = "",
        date_start: Optional[Any] = None,
        date_end: Optional[Any] = None,
        representative: Optional[str] = None,
        customer: Optional[str] = None,
        region: Optional[str] = None,
    ) -> pd.DataFrame:
        """Applies dashboard filters to the loaded sales dataset."""
        filtered_df = self.df.copy()

        if status_filter != "Todos":
            normalized_status = filtered_df["Status da Nota Fiscal"].apply(SalesAnalytics._normalize_status)
            non_emitted = normalized_status.isin(["NAO_TRANSMITIDA", "NAO EMITIDA"])

            if status_filter == "Com NF Emitida":
                filtered_df = filtered_df[~non_emitted]
            elif status_filter == "Sem NF Emitida":
                filtered_df = filtered_df[non_emitted]
            else:
                target_status = SalesAnalytics._normalize_status(status_filter)
                filtered_df = filtered_df[normalized_status == target_status]

        if search_product:
            filtered_df = filtered_df[
                filtered_df["Código do Produto"].astype(str).str.contains(search_product, case=False, na=False)
            ]

        if date_start is not None or date_end is not None:
            date_col = self._find_date_column(filtered_df)
            if date_col and date_col in filtered_df.columns:
                filtered_df[date_col] = pd.to_datetime(filtered_df[date_col], errors="coerce")
                mask = pd.Series(True, index=filtered_df.index)
                if date_start is not None:
                    mask &= filtered_df[date_col] >= pd.Timestamp(date_start)
                if date_end is not None:
                    mask &= filtered_df[date_col] <= pd.Timestamp(date_end)
                filtered_df = filtered_df.loc[mask]

        if representative not in {None, "", "Todos"} and "Representante" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Representante"].astype(str).str.strip() == representative]

        if customer not in {None, "", "Todos"}:
            customer_key = SalesAnalytics._coerce_customer_key(filtered_df)
            filtered_df = filtered_df[customer_key.astype(str).str.contains(customer, case=False, na=False)]

        if region not in {None, "", "Todos"} and "UF" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["UF"].astype(str).str.strip().str.upper() == region.upper()]

        return filtered_df

    @staticmethod
    def calculate_kpis(df: pd.DataFrame) -> dict[str, Any]:
        """Calculates core operational and fiscal KPIs.

        Formula
        -------
        nf_emission_rate = orders_with_nf / total_orders * 100
        orders_per_customer = total_orders / active_customers
        """
        return calculate_core_sales_kpis(df)

    @staticmethod
    def get_customer_summary(df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates customers by orders, revenue and average ticket."""
        return summarize_customers(df)

    def build_profitability_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """Builds unified profitability dataset from sales and product catalog.

        Formula
        -------
        Faturamento = PU de saida * Quantidade
        Custo Total = (PU de entrada * Quantidade) + (Faturamento * Custo Variavel %)
        Margem de contribuicao = Faturamento - Custo Total
        Margem Bruta (%) = Margem de contribuicao / Faturamento * 100
        """
        return build_profitability_dataset(df, self.products_df)

    def calculate_financial_kpis(self, profitability_df: pd.DataFrame) -> dict[str, Any]:
        """Calculates financial KPIs using the profitability source of truth."""
        return calculate_financial_kpis(profitability_df, fixed_cost_pct=LUCRO_OPERACIONAL_CUSTO_FIXO)

    def get_profitability_by_product(self, profitability_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates profitability metrics per product."""
        return summarize_profitability_by_product(profitability_df)

    def get_profitability_by_representative(self, profitability_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates profitability metrics per representative."""
        return summarize_profitability_by_representative(profitability_df)

    def get_profitability_by_customer(self, profitability_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates profitability metrics per customer."""
        return summarize_profitability_by_customer(profitability_df)

    def get_monthly_profitability(self, profitability_df: pd.DataFrame) -> pd.DataFrame:
        """Builds monthly profitability trend dataset."""
        date_column = self._find_date_column(profitability_df)
        return summarize_monthly_profitability(profitability_df, date_column)

    @staticmethod
    def get_abc_analysis(df: pd.DataFrame, value_col: str) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Performs ABC classification over a numeric value column."""
        return build_abc_analysis(df, value_col)

    @staticmethod
    def get_abc_pareto_analysis(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Performs product ABC/Pareto by sold quantity."""
        return build_abc_pareto_analysis(df)

    @staticmethod
    def get_order_stats(df: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame]:
        """Calculates order quantity distribution metrics."""
        return calculate_order_stats(df)

    @staticmethod
    def get_fiscal_distribution(df: pd.DataFrame) -> pd.DataFrame:
        """Calculates fiscal status distribution for unique orders."""
        return calculate_fiscal_distribution(df)

    @staticmethod
    def _find_date_column(df: pd.DataFrame) -> str | None:
        """Finds a parsable date column from candidate names."""
        if df.empty:
            return None

        candidates = [col for col in df.columns if "data" in col.lower() or "date" in col.lower()]
        for col in candidates:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().any():
                return col
        return None

    @staticmethod
    def _client_identifier(df: pd.DataFrame) -> pd.Series:
        """Compatibility alias for customer key generation."""
        return SalesAnalytics._coerce_customer_key(df)

    @staticmethod
    def _ensure_representante_column(df: pd.DataFrame) -> pd.DataFrame:
        """Ensures representative column exists and has non-empty values."""
        if df is None or df.empty:
            return df

        default_rep = os.getenv("NOME_PADRAO_REPRESENTANTE", "Leonardo")
        normalized_df = df.copy()

        if "Representante" not in normalized_df.columns:
            normalized_df["Representante"] = default_rep
            return normalized_df

        normalized_df["Representante"] = normalized_df["Representante"].astype(str).str.strip()
        normalized_df.loc[normalized_df["Representante"].isin(["", "N/A", "nan", "None", "<NA>"]), "Representante"] = default_rep
        return normalized_df

    @staticmethod
    def get_representative_sales_summary(df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates representative performance summary."""
        return summarize_representative_sales(df)

    @staticmethod
    def get_representative_repurchase_rate(df: pd.DataFrame) -> pd.DataFrame:
        """Returns representative repurchase rates from performance base."""
        performance_df = calculate_representative_performance(df)
        if performance_df.empty:
            return pd.DataFrame()
        columns = ["Representante", "Clientes_Recorrentes", "Clientes_Total", "Recompra (%)"]
        available_columns = [column for column in columns if column in performance_df.columns]
        return performance_df[available_columns].copy()

    @staticmethod
    def get_representative_monthly_evolution(df: pd.DataFrame) -> pd.DataFrame:
        """Builds representative monthly revenue evolution."""
        date_column = SalesAnalytics._find_date_column(df)
        return build_representative_monthly_evolution(df, date_column)

    @staticmethod
    def get_representative_meta(df: pd.DataFrame) -> pd.DataFrame:
        """Returns representative sales target aggregation when available."""
        if df is None or df.empty:
            return pd.DataFrame()

        normalized_df = SalesAnalytics._ensure_representante_column(df)
        if "Meta" not in normalized_df.columns and "meta" not in normalized_df.columns:
            return pd.DataFrame()

        meta_column = "Meta" if "Meta" in normalized_df.columns else "meta"
        normalized_df[meta_column] = pd.to_numeric(normalized_df[meta_column], errors="coerce").fillna(0.0)
        return normalized_df.groupby("Representante", dropna=False, as_index=False).agg(Meta_Valor=(meta_column, "sum"))

    @staticmethod
    def get_revenue_by_city(df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates revenue and customers by city."""
        return calculate_revenue_by_city(df)

    @staticmethod
    def get_clients_by_state(df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates unique customers by state."""
        return calculate_clients_by_state(df)

    @staticmethod
    def get_state_revenue(df: pd.DataFrame) -> pd.DataFrame:
        """Aggregates revenue, customers and orders by state."""
        return calculate_state_revenue(df)

    @staticmethod
    def load_product_code_mapping() -> dict[str, str]:
        """Loads old/new product code mapping from historical workbook."""
        repository = SalesRepository()
        return repository.load_product_code_mapping()

    @staticmethod
    def get_state_ticket_average(df: pd.DataFrame) -> pd.DataFrame:
        """Calculates average ticket by state with configurable threshold."""
        return calculate_state_ticket_average(df, min_orders_threshold=MIN_PED_TICKET_MEDIO)

    @staticmethod
    def get_top_cities_by_revenue(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """Returns top cities by total revenue."""
        return top_cities_by_revenue(df, top_n)

    @staticmethod
    def get_top_cities_by_customers(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """Returns top cities by unique customer base."""
        return top_cities_by_customers(df, top_n)

    @staticmethod
    def get_state_geo_coordinates(df: pd.DataFrame) -> pd.DataFrame:
        """Returns state ticket summary enriched with geo coordinates."""
        return calculate_state_geo_coordinates(df)

    @staticmethod
    def get_representative_performance(df: pd.DataFrame) -> pd.DataFrame:
        """Consolidates representative performance indicators."""
        return calculate_representative_performance(df)
