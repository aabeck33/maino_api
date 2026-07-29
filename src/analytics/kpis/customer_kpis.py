"""Customer-centric KPI calculations."""

from __future__ import annotations

import pandas as pd

from analytics.kpis.shared import coerce_customer_key, revenue_series


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
    customer_summary_df = (
        customer_summary_df.groupby("Cliente_Chave", dropna=False, as_index=False)
        .agg(
            Pedidos=("Pedido ID", "nunique"),
            Receita_Total=("Valor Total", "sum"),
        )
    )
    customer_summary_df["Ticket Médio"] = customer_summary_df.apply(
        lambda row: row["Receita_Total"] / row["Pedidos"] if row["Pedidos"] > 0 else 0.0,
        axis=1,
    )

    return customer_summary_df.sort_values("Pedidos", ascending=False).reset_index(drop=True)
