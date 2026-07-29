"""Application service orchestrating repositories and KPI modules."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import pandas as pd

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


FIXED_COST_PCT = float(os.getenv("LUCRO_OPERACIONAL_CUSTO_FIXO", "25"))


@dataclass(frozen=True)
class DashboardSnapshot:
    """Container for precomputed data consumed by dashboard and PDF."""

    filtered_sales_df: pd.DataFrame
    core_kpis: dict[str, Any]
    profitability_df: pd.DataFrame
    financial_kpis: dict[str, Any]
    product_profitability_df: pd.DataFrame
    representative_profitability_df: pd.DataFrame
    customer_profitability_df: pd.DataFrame
    monthly_profitability_df: pd.DataFrame


class DashboardDataService:
    """Coordinates repositories and KPI calculators as a single entrypoint."""

    def __init__(
        self,
        sales_file_path: Path | None = None,
        products_file_path: Path | None = None,
        customers_file_path: Path | None = None,
    ) -> None:
        self.sales_repository = SalesRepository()
        self.product_repository = ProductRepository()
        self.customer_repository = CustomerRepository()

        self.sales_file_path = sales_file_path or SETTINGS.data_file_path(SETTINGS.data_files.sales_orders)
        self.products_file_path = products_file_path or SETTINGS.data_file_path(SETTINGS.data_files.products)
        self.customers_file_path = customers_file_path or SETTINGS.data_file_path(SETTINGS.data_files.customers)

        self.products_df = self.product_repository.load_catalog(self.products_file_path)
        sales_df = self.sales_repository.load_sales_orders(self.sales_file_path)
        product_mapping = self.sales_repository.load_product_code_mapping()
        mapped_sales_df = self.sales_repository.apply_product_code_mapping(sales_df, product_mapping)
        self.sales_df = self.customer_repository.enrich_sales_with_customer_master(mapped_sales_df)

    @staticmethod
    def find_date_column(dataframe: pd.DataFrame) -> str | None:
        """Finds a viable date column in a dataframe."""
        if dataframe.empty:
            return None

        date_candidates = [column for column in dataframe.columns if "data" in column.lower() or "date" in column.lower()]
        for date_column in date_candidates:
            if pd.api.types.is_datetime64_any_dtype(dataframe[date_column]):
                return date_column
            parsed_series = pd.to_datetime(dataframe[date_column], errors="coerce")
            if parsed_series.notna().any():
                return date_column
        return None

    def get_filtered_data(
        self,
        status_filter: str = "Todos",
        search_product: str = "",
        date_start: Any | None = None,
        date_end: Any | None = None,
        representative: str | None = None,
        customer: str | None = None,
        region: str | None = None,
    ) -> pd.DataFrame:
        """Applies global dashboard filters on sales dataset."""
        filtered_df = self.sales_df.copy()

        if status_filter != "Todos":
            non_emitted_mask = filtered_df["Status da Nota Fiscal"].apply(self.sales_repository.is_non_emitted_invoice)
            if status_filter == "Com NF Emitida":
                filtered_df = filtered_df[~non_emitted_mask]
            elif status_filter == "Sem NF Emitida":
                filtered_df = filtered_df[non_emitted_mask]
            else:
                target_normalized = status_filter.strip().upper()
                filtered_df = filtered_df[
                    filtered_df["Status da Nota Fiscal"].astype(str).str.strip().str.upper() == target_normalized
                ]

        if search_product:
            filtered_df = filtered_df[
                filtered_df["Código do Produto"].astype(str).str.contains(search_product, case=False, na=False)
            ]

        if date_start is not None or date_end is not None:
            date_column = self.find_date_column(filtered_df)
            if date_column and date_column in filtered_df.columns:
                filtered_df[date_column] = pd.to_datetime(filtered_df[date_column], errors="coerce")
                mask = pd.Series(True, index=filtered_df.index)
                if date_start is not None:
                    mask &= filtered_df[date_column] >= pd.Timestamp(date_start)
                if date_end is not None:
                    mask &= filtered_df[date_column] <= pd.Timestamp(date_end)
                filtered_df = filtered_df.loc[mask]

        if representative not in {None, "", "Todos"} and "Representante" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Representante"].astype(str).str.strip() == representative]

        if customer not in {None, "", "Todos"}:
            customer_key = filtered_df.get("Cliente", filtered_df.get("Nome do Cliente", "")).astype(str)
            filtered_df = filtered_df[customer_key.str.contains(customer, case=False, na=False)]

        if region not in {None, "", "Todos"} and "UF" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["UF"].astype(str).str.strip().str.upper() == str(region).upper()]

        return filtered_df

    def build_snapshot(self, filtered_df: pd.DataFrame) -> DashboardSnapshot:
        """Builds all primary datasets used by dashboard and PDF presentation layers."""
        profitability_df = build_profitability_dataset(filtered_df, self.products_df)
        financial_kpis = calculate_financial_kpis(profitability_df, fixed_cost_pct=FIXED_COST_PCT)

        date_column = self.find_date_column(profitability_df)
        monthly_profitability_df = summarize_monthly_profitability(profitability_df, date_column)

        return DashboardSnapshot(
            filtered_sales_df=filtered_df,
            core_kpis=calculate_core_sales_kpis(filtered_df),
            profitability_df=profitability_df,
            financial_kpis=financial_kpis,
            product_profitability_df=summarize_profitability_by_product(profitability_df),
            representative_profitability_df=summarize_profitability_by_representative(profitability_df),
            customer_profitability_df=summarize_profitability_by_customer(profitability_df),
            monthly_profitability_df=monthly_profitability_df,
        )

    # Proxy methods for compatibility with existing callers
    @staticmethod
    def calculate_kpis(sales_df: pd.DataFrame) -> dict[str, Any]:
        return calculate_core_sales_kpis(sales_df)

    @staticmethod
    def calculate_financial_kpis(profitability_df: pd.DataFrame) -> dict[str, Any]:
        return calculate_financial_kpis(profitability_df, fixed_cost_pct=FIXED_COST_PCT)

    @staticmethod
    def get_customer_summary(sales_df: pd.DataFrame) -> pd.DataFrame:
        return summarize_customers(sales_df)

    @staticmethod
    def get_abc_analysis(dataframe: pd.DataFrame, value_column: str) -> tuple[pd.DataFrame, dict[str, int]]:
        return build_abc_analysis(dataframe, value_column)

    @staticmethod
    def get_abc_pareto_analysis(sales_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
        return build_abc_pareto_analysis(sales_df)

    @staticmethod
    def get_order_stats(sales_df: pd.DataFrame) -> tuple[dict[str, float], pd.DataFrame]:
        return calculate_order_stats(sales_df)

    @staticmethod
    def get_fiscal_distribution(sales_df: pd.DataFrame) -> pd.DataFrame:
        return calculate_fiscal_distribution(sales_df)

    @staticmethod
    def get_representative_sales_summary(sales_df: pd.DataFrame) -> pd.DataFrame:
        return summarize_representative_sales(sales_df)

    def get_representative_monthly_evolution(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        return build_representative_monthly_evolution(sales_df, self.find_date_column(sales_df))

    @staticmethod
    def get_representative_performance(sales_df: pd.DataFrame) -> pd.DataFrame:
        return calculate_representative_performance(sales_df)

    @staticmethod
    def get_revenue_by_city(sales_df: pd.DataFrame) -> pd.DataFrame:
        return calculate_revenue_by_city(sales_df)

    @staticmethod
    def get_clients_by_state(sales_df: pd.DataFrame) -> pd.DataFrame:
        return calculate_clients_by_state(sales_df)

    @staticmethod
    def get_state_revenue(sales_df: pd.DataFrame) -> pd.DataFrame:
        return calculate_state_revenue(sales_df)

    @staticmethod
    def get_state_ticket_average(sales_df: pd.DataFrame) -> pd.DataFrame:
        return calculate_state_ticket_average(sales_df)

    @staticmethod
    def get_top_cities_by_revenue(sales_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        return top_cities_by_revenue(sales_df, top_n)

    @staticmethod
    def get_top_cities_by_customers(sales_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        return top_cities_by_customers(sales_df, top_n)

    @staticmethod
    def get_state_geo_coordinates(sales_df: pd.DataFrame) -> pd.DataFrame:
        return calculate_state_geo_coordinates(sales_df)

    def build_profitability_dataset(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        return build_profitability_dataset(sales_df, self.products_df)

    @staticmethod
    def get_profitability_by_product(profitability_df: pd.DataFrame) -> pd.DataFrame:
        return summarize_profitability_by_product(profitability_df)

    @staticmethod
    def get_profitability_by_representative(profitability_df: pd.DataFrame) -> pd.DataFrame:
        return summarize_profitability_by_representative(profitability_df)

    @staticmethod
    def get_profitability_by_customer(profitability_df: pd.DataFrame) -> pd.DataFrame:
        return summarize_profitability_by_customer(profitability_df)

    def get_monthly_profitability(self, profitability_df: pd.DataFrame) -> pd.DataFrame:
        return summarize_monthly_profitability(profitability_df, self.find_date_column(profitability_df))
