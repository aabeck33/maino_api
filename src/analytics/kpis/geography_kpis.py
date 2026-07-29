"""Geography-oriented KPI calculations and aggregations."""

from __future__ import annotations

import os
import pandas as pd

from analytics.kpis.shared import coerce_customer_key
from utils.geo import BRAZIL_STATE_CENTROIDS, map_cep_to_uf


def _normalize_geo_data(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes raw sales fields used by geography calculations."""
    if sales_df.empty:
        return sales_df.copy()

    normalized_df = sales_df.copy()
    normalized_df["CEP"] = normalized_df.get("CEP", "").astype(str).str.strip().fillna("")
    if "UF" not in normalized_df.columns:
        normalized_df["UF"] = "N/A"
    if "Cidade" not in normalized_df.columns:
        normalized_df["Cidade"] = "N/A"
    if "Valor Total" not in normalized_df.columns:
        normalized_df["Valor Total"] = 0.0

    normalized_df["UF"] = normalized_df["UF"].astype(str).str.strip().str.upper().replace({"": "N/A", "NONE": "N/A"})
    normalized_df["Cidade"] = normalized_df["Cidade"].astype(str).str.strip().replace({"": "N/A", "None": "N/A", "nan": "N/A"})
    normalized_df["Valor Total"] = pd.to_numeric(normalized_df["Valor Total"], errors="coerce").fillna(0.0)

    def resolve_uf(row: pd.Series) -> str:
        if row["UF"] not in {"", "N/A", "NONE"}:
            return row["UF"]
        return map_cep_to_uf(row["CEP"])

    normalized_df["UF"] = normalized_df.apply(resolve_uf, axis=1)
    normalized_df.loc[normalized_df["UF"] == "", "UF"] = "N/A"

    return normalized_df


def _build_order_summary(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates line-items into order-level summaries for geo analytics."""
    if sales_df.empty:
        return pd.DataFrame()

    normalized_df = _normalize_geo_data(sales_df)
    normalized_df["Cliente_Chave"] = coerce_customer_key(normalized_df)
    if "Representante" not in normalized_df.columns:
        normalized_df["Representante"] = "N/A"

    order_summary_df = normalized_df.groupby(["Pedido ID", "Número do Pedido"], dropna=False, as_index=False).agg(
        CEP=("CEP", "first"),
        UF=("UF", lambda values: next((value for value in values if value not in {"", "N/A"}), "N/A")),
        Cidade=("Cidade", lambda values: next((value for value in values if value not in {"", "N/A"}), "N/A")),
        Valor_Total=("Valor Total", "first"),
        Status_da_Nota_Fiscal=("Status da Nota Fiscal", "first"),
        Representante=("Representante", "first"),
        Cliente_Chave=("Cliente_Chave", "first"),
    )
    order_summary_df["Valor_Total"] = pd.to_numeric(order_summary_df["Valor_Total"], errors="coerce").fillna(0.0)

    return order_summary_df


def calculate_revenue_by_city(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates total revenue and customer base per city."""
    order_summary_df = _build_order_summary(sales_df)
    if order_summary_df.empty:
        return pd.DataFrame()

    city_revenue_df = order_summary_df.groupby("Cidade", dropna=False, as_index=False).agg(
        Valor_Total=("Valor_Total", "sum"),
        Clientes=("Cliente_Chave", "nunique"),
    )
    return city_revenue_df.sort_values("Valor_Total", ascending=False)


def calculate_clients_by_state(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates unique customers per state."""
    order_summary_df = _build_order_summary(sales_df)
    if order_summary_df.empty:
        return pd.DataFrame()

    state_clients_df = order_summary_df.groupby("UF", dropna=False, as_index=False).agg(Clientes=("Cliente_Chave", "nunique"))
    return state_clients_df.sort_values("Clientes", ascending=False)


def calculate_state_revenue(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates revenue, customers and orders by state."""
    order_summary_df = _build_order_summary(sales_df)
    if order_summary_df.empty:
        return pd.DataFrame()

    state_revenue_df = order_summary_df.groupby("UF", dropna=False, as_index=False).agg(
        Valor_Total=("Valor_Total", "sum"),
        Clientes=("Cliente_Chave", "nunique"),
        Pedidos=("Pedido ID", "nunique"),
    )
    return state_revenue_df.sort_values("Valor_Total", ascending=False)


def calculate_state_ticket_average(sales_df: pd.DataFrame, min_orders_threshold: int | None = None) -> pd.DataFrame:
    """Calculates average ticket per state with statistical threshold."""
    state_revenue_df = calculate_state_revenue(sales_df)
    if state_revenue_df.empty:
        return pd.DataFrame()

    threshold = min_orders_threshold if min_orders_threshold is not None else int(os.getenv("MIN_PED_TICKET_MEDIO", "1"))
    filtered_state_df = state_revenue_df[state_revenue_df["Pedidos"] >= threshold].copy()
    if filtered_state_df.empty:
        return pd.DataFrame()

    filtered_state_df["Ticket Médio"] = filtered_state_df.apply(
        lambda row: row["Valor_Total"] / row["Clientes"] if row["Clientes"] > 0 else 0.0,
        axis=1,
    )
    filtered_state_df["Participação Clientes (%)"] = filtered_state_df["Clientes"] / filtered_state_df["Clientes"].sum() * 100
    filtered_state_df["Participação Receita (%)"] = filtered_state_df["Valor_Total"] / filtered_state_df["Valor_Total"].sum() * 100

    return filtered_state_df.sort_values("Ticket Médio", ascending=False)


def top_cities_by_revenue(sales_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Returns top cities ranked by revenue."""
    return calculate_revenue_by_city(sales_df).head(top_n)


def top_cities_by_customers(sales_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Returns top cities ranked by unique customers."""
    city_summary_df = calculate_revenue_by_city(sales_df)
    return city_summary_df.sort_values("Clientes", ascending=False).head(top_n)


def calculate_state_geo_coordinates(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Adds latitude and longitude centroid for each state in ticket summary."""
    state_ticket_df = calculate_state_ticket_average(sales_df)
    if state_ticket_df.empty:
        return pd.DataFrame()

    coordinates = [BRAZIL_STATE_CENTROIDS.get(uf, (None, None)) for uf in state_ticket_df["UF"]]
    state_ticket_df["Latitude"] = [lat for lat, _ in coordinates]
    state_ticket_df["Longitude"] = [lon for _, lon in coordinates]

    return state_ticket_df[state_ticket_df["Latitude"].notna() & state_ticket_df["Longitude"].notna()].copy()
