"""Sales KPI calculations and ABC/Pareto analytics."""

from __future__ import annotations

from typing import Any
import unicodedata
import pandas as pd

from analytics.kpis.shared import coerce_customer_key


def normalize_status(status: Any) -> str:
    """Normalizes fiscal status strings to stable uppercase tokens."""
    if status is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(status).strip().upper())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def calculate_core_sales_kpis(sales_df: pd.DataFrame) -> dict[str, Any]:
    """Calculates high-level operational and fiscal KPIs.

    Parameters
    ----------
    sales_df : pd.DataFrame
        Sales rows filtered or unfiltered.

    Returns
    -------
    dict[str, Any]
        Dictionary containing order, customer, product, and fiscal KPIs.
    """
    if sales_df.empty:
        return {
            "total_orders": 0,
            "total_products": 0,
            "total_qty_sold": 0.0,
            "unique_products": 0,
            "active_customers": 0,
            "orders_per_customer": 0.0,
            "orders_with_nf": 0,
            "orders_without_nf": 0,
            "nf_emission_rate": 0.0,
        }

    total_orders = sales_df["Pedido ID"].nunique()
    total_qty_sold = sales_df["Quantidade"].sum()
    unique_products = sales_df["Código do Produto"].nunique()

    unique_orders_df = sales_df.drop_duplicates(subset=["Pedido ID"])
    normalized_status = unique_orders_df["Status da Nota Fiscal"].apply(normalize_status)
    orders_without_nf = unique_orders_df[normalized_status.isin(["NAO_TRANSMITIDA", "NAO EMITIDA"])]["Pedido ID"].count()
    orders_with_nf = total_orders - orders_without_nf

    customer_key = coerce_customer_key(sales_df)
    active_customers = customer_key.replace(["", "N/A", "nan", "None", "<NA>"], pd.NA).dropna().nunique()
    orders_per_customer = total_orders / active_customers if active_customers > 0 else 0.0
    nf_emission_rate = (orders_with_nf / total_orders * 100) if total_orders > 0 else 0.0

    return {
        "total_orders": total_orders,
        "total_products": unique_products,
        "total_qty_sold": total_qty_sold,
        "unique_products": unique_products,
        "active_customers": active_customers,
        "orders_per_customer": orders_per_customer,
        "orders_with_nf": orders_with_nf,
        "orders_without_nf": orders_without_nf,
        "nf_emission_rate": nf_emission_rate,
    }


def build_abc_analysis(input_df: pd.DataFrame, value_column: str) -> tuple[pd.DataFrame, dict[str, int]]:
    """Classifies rows into ABC classes based on cumulative share of a value column."""
    if input_df.empty:
        return pd.DataFrame(), {"A": 0, "B": 0, "C": 0}

    classified_df = input_df.copy().sort_values(by=value_column, ascending=False).reset_index(drop=True)
    total_value = classified_df[value_column].sum()
    classified_df["Participação (%)"] = (classified_df[value_column] / total_value * 100) if total_value > 0 else 0.0
    classified_df["Acumulado (%)"] = classified_df["Participação (%)"].cumsum()

    classes = []
    for cumulative_pct in classified_df["Acumulado (%)"]:
        if cumulative_pct <= 80.0:
            classes.append("A")
        elif cumulative_pct <= 95.0:
            classes.append("B")
        else:
            classes.append("C")
    classified_df["Classe ABC"] = classes

    class_counts = classified_df["Classe ABC"].value_counts().to_dict()
    for class_name in ["A", "B", "C"]:
        class_counts.setdefault(class_name, 0)

    return classified_df, class_counts


def build_abc_pareto_analysis(sales_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Computes product-level Pareto and ABC using sold quantity as driver."""
    if sales_df.empty:
        return pd.DataFrame(), {"A": 0, "B": 0, "C": 0}

    product_quantity_df = sales_df.groupby("Código do Produto")["Quantidade"].sum().reset_index()
    product_quantity_df = product_quantity_df.sort_values(by="Quantidade", ascending=False).reset_index(drop=True)

    total_qty = product_quantity_df["Quantidade"].sum()
    product_quantity_df["Participação (%)"] = (product_quantity_df["Quantidade"] / total_qty * 100) if total_qty > 0 else 0.0
    product_quantity_df["Acumulado"] = product_quantity_df["Quantidade"].cumsum()
    product_quantity_df["Acumulado (%)"] = (product_quantity_df["Acumulado"] / total_qty * 100) if total_qty > 0 else 0.0

    classes = []
    for index, cumulative_pct in enumerate(product_quantity_df["Acumulado (%)"]):
        if index == 0 or cumulative_pct <= 80.0:
            classes.append("A")
        elif cumulative_pct <= 95.0:
            classes.append("B")
        else:
            classes.append("C")
    product_quantity_df["Classe ABC"] = classes

    class_counts = product_quantity_df["Classe ABC"].value_counts().to_dict()
    for class_name in ["A", "B", "C"]:
        class_counts.setdefault(class_name, 0)

    return product_quantity_df, class_counts


def calculate_order_stats(sales_df: pd.DataFrame) -> tuple[dict[str, float], pd.DataFrame]:
    """Calculates order-level quantity distribution statistics."""
    if sales_df.empty:
        return {"mean": 0.0, "median": 0.0, "max": 0.0, "min": 0.0}, pd.DataFrame()

    order_quantity_df = sales_df.groupby(["Pedido ID", "Número do Pedido"])["Quantidade"].sum().reset_index()
    statistics = {
        "mean": order_quantity_df["Quantidade"].mean(),
        "median": order_quantity_df["Quantidade"].median(),
        "max": order_quantity_df["Quantidade"].max(),
        "min": order_quantity_df["Quantidade"].min(),
    }
    largest_orders_df = order_quantity_df.sort_values(by="Quantidade", ascending=False).reset_index(drop=True)
    return statistics, largest_orders_df


def calculate_fiscal_distribution(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates fiscal status distribution considering unique orders."""
    if sales_df.empty:
        return pd.DataFrame()

    unique_orders_df = sales_df.drop_duplicates(subset=["Pedido ID"])
    fiscal_df = unique_orders_df.groupby("Status da Nota Fiscal")["Pedido ID"].count().reset_index(name="Quantidade")
    total_orders = fiscal_df["Quantidade"].sum()
    fiscal_df["Percentual (%)"] = (fiscal_df["Quantidade"] / total_orders * 100) if total_orders > 0 else 0.0
    return fiscal_df
