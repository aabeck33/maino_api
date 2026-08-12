"""Customer-centric KPI calculations."""

from __future__ import annotations

import unicodedata
import pandas as pd

from analytics.kpis.shared import coerce_customer_key, revenue_series


def _normalize_text(value: object) -> str:
    """Normalizes text for stable case/accent-insensitive matching."""
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value).strip().upper())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _is_fdy_distributor_tag(value: object) -> bool:
    """Checks whether tag text marks the customer as Distribuidor FDY."""
    return "DISTRIBUIDOR FDY" in _normalize_text(value)


def summarize_customers(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Builds customer summary with order volume, revenue and average ticket.

    Parameters
    ----------
    sales_df : pd.DataFrame
        Source sales rows.

    Returns
    -------
    pd.DataFrame
        Customer-level summary sorted by number of orders.
    """
    if sales_df.empty:
        return pd.DataFrame()

    customer_summary_df = sales_df.copy()
    customer_summary_df["Cliente_Chave"] = coerce_customer_key(customer_summary_df)
    customer_summary_df["Valor Total"] = revenue_series(customer_summary_df, value_column="Valor Total")
    tags_series = customer_summary_df.get("Tags", pd.Series("", index=customer_summary_df.index, dtype="object"))
    if "Tags_master" in customer_summary_df.columns:
        tags_series = tags_series.fillna("").astype(str).where(
            tags_series.fillna("").astype(str).str.strip().ne(""),
            customer_summary_df["Tags_master"],
        )
    customer_summary_df["Distribuidor_FDY"] = tags_series.apply(_is_fdy_distributor_tag)
    customer_summary_df = (
        customer_summary_df.groupby("Cliente_Chave", dropna=False, as_index=False)
        .agg(
            Pedidos=("Pedido ID", "nunique"),
            Receita_Total=("Valor Total", "sum"),
            Distribuidor_FDY=("Distribuidor_FDY", "max"),
        )
    )
    customer_summary_df["Ticket Médio"] = customer_summary_df.apply(
        lambda row: row["Receita_Total"] / row["Pedidos"] if row["Pedidos"] > 0 else 0.0,
        axis=1,
    )
    customer_summary_df["Distribuidor FDY"] = customer_summary_df["Distribuidor_FDY"].map({True: "Sim", False: "Não"})

    return customer_summary_df.sort_values(
        by=["Distribuidor_FDY", "Pedidos"],
        ascending=[True, False],
    ).reset_index(drop=True)
