"""Representative performance and evolution KPI calculations."""

from __future__ import annotations

import pandas as pd

from analytics.kpis.shared import coerce_customer_key


def _ensure_representative_column(sales_df: pd.DataFrame, default_representative: str = "Leonardo") -> pd.DataFrame:
    """Ensures representative column exists and has non-empty values."""
    if sales_df is None or sales_df.empty:
        return sales_df

    normalized_df = sales_df.copy()
    if "Representante" not in normalized_df.columns:
        normalized_df["Representante"] = default_representative
        return normalized_df

    normalized_df["Representante"] = normalized_df["Representante"].astype(str).str.strip()
    normalized_df.loc[normalized_df["Representante"].isin(["", "N/A", "nan", "None", "<NA>"]), "Representante"] = default_representative
    return normalized_df


def summarize_representative_sales(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Summarizes representative commercial performance."""
    if sales_df is None or sales_df.empty:
        return pd.DataFrame()

    normalized_df = _ensure_representative_column(sales_df)
    normalized_df["Cliente_Chave"] = coerce_customer_key(normalized_df)

    orders_df = normalized_df.groupby(["Pedido ID", "Número do Pedido"], dropna=False, as_index=False).agg(
        Representante=("Representante", "first"),
        Valor_Total=("Valor Total", "first"),
        Cliente_Chave=("Cliente_Chave", "first"),
    )
    orders_df["Valor_Total"] = pd.to_numeric(orders_df["Valor_Total"], errors="coerce").fillna(0.0)

    summary_df = (
        orders_df.groupby("Representante", dropna=False, as_index=False)
        .agg(
            Receita_Total=("Valor_Total", "sum"),
            Pedidos=("Pedido ID", "nunique"),
            Clientes_Unicos=("Cliente_Chave", "nunique"),
        )
    )

    if "Código do Produto" in normalized_df.columns:
        product_mix_df = (
            normalized_df.groupby("Representante", dropna=False)["Código do Produto"]
            .nunique()
            .reset_index(name="Produtos_Distintos")
        )
        summary_df = summary_df.merge(product_mix_df, on="Representante", how="left")
    else:
        summary_df["Produtos_Distintos"] = 0

    summary_df["Ticket_Medio"] = summary_df.apply(
        lambda row: row["Receita_Total"] / row["Pedidos"] if row["Pedidos"] > 0 else 0.0,
        axis=1,
    )
    summary_df["Pedidos_por_Cliente"] = summary_df.apply(
        lambda row: row["Pedidos"] / row["Clientes_Unicos"] if row["Clientes_Unicos"] > 0 else 0.0,
        axis=1,
    )

    total_revenue = summary_df["Receita_Total"].sum()
    summary_df["Participacao (%)"] = summary_df.apply(
        lambda row: row["Receita_Total"] / total_revenue * 100 if total_revenue > 0 else 0.0,
        axis=1,
    )

    return summary_df.sort_values(by="Receita_Total", ascending=False).reset_index(drop=True)


def _calculate_repurchase_rate(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates representative repurchase rate based on customer recurrence."""
    if sales_df is None or sales_df.empty:
        return pd.DataFrame()

    normalized_df = _ensure_representative_column(sales_df)
    normalized_df["Cliente_Chave"] = coerce_customer_key(normalized_df)

    client_orders_df = (
        normalized_df.groupby(["Representante", "Cliente_Chave"], dropna=False)["Pedido ID"]
        .nunique()
        .reset_index(name="Orders_per_Client")
    )

    repurchase_df = (
        client_orders_df.groupby("Representante", dropna=False, as_index=False)
        .agg(
            Clientes_Recorrentes=("Orders_per_Client", lambda values: (values > 1).sum()),
            Clientes_Total=("Orders_per_Client", "count"),
        )
    )
    repurchase_df["Recompra (%)"] = repurchase_df.apply(
        lambda row: row["Clientes_Recorrentes"] / row["Clientes_Total"] * 100 if row["Clientes_Total"] > 0 else 0.0,
        axis=1,
    )

    return repurchase_df


def _calculate_representative_meta(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates sales targets by representative when provided in dataset."""
    if sales_df is None or sales_df.empty:
        return pd.DataFrame()

    normalized_df = _ensure_representative_column(sales_df)
    if "Meta" not in normalized_df.columns and "meta" not in normalized_df.columns:
        return pd.DataFrame()

    meta_column = "Meta" if "Meta" in normalized_df.columns else "meta"
    normalized_df[meta_column] = pd.to_numeric(normalized_df[meta_column], errors="coerce").fillna(0.0)

    return normalized_df.groupby("Representante", dropna=False, as_index=False).agg(Meta_Valor=(meta_column, "sum"))


def calculate_representative_performance(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Builds complete representative performance dashboard base."""
    if sales_df is None or sales_df.empty:
        return pd.DataFrame()

    summary_df = summarize_representative_sales(sales_df)
    if summary_df.empty:
        return summary_df

    repurchase_df = _calculate_repurchase_rate(sales_df)
    if not repurchase_df.empty:
        summary_df = summary_df.merge(
            repurchase_df[["Representante", "Clientes_Recorrentes", "Clientes_Total", "Recompra (%)"]],
            on="Representante",
            how="left",
        )

    representative_meta_df = _calculate_representative_meta(sales_df)
    if not representative_meta_df.empty:
        summary_df = summary_df.merge(representative_meta_df, on="Representante", how="left")
        summary_df["Atingimento (%)"] = summary_df.apply(
            lambda row: row["Receita_Total"] / row["Meta_Valor"] * 100 if row["Meta_Valor"] > 0 else 0.0,
            axis=1,
        )

    return summary_df.sort_values(by="Receita_Total", ascending=False).reset_index(drop=True)


def build_representative_monthly_evolution(sales_df: pd.DataFrame, date_column: str | None) -> pd.DataFrame:
    """Builds monthly representative revenue trends."""
    if sales_df is None or sales_df.empty or date_column is None:
        return pd.DataFrame()

    normalized_df = _ensure_representative_column(sales_df)
    normalized_df[date_column] = pd.to_datetime(normalized_df[date_column], errors="coerce")
    normalized_df = normalized_df[normalized_df[date_column].notna()]
    if normalized_df.empty:
        return pd.DataFrame()

    normalized_df["Mes"] = normalized_df[date_column].dt.to_period("M").dt.to_timestamp()
    orders_df = normalized_df.groupby(["Pedido ID", "Número do Pedido"], dropna=False, as_index=False).agg(
        Representante=("Representante", "first"),
        Mes=("Mes", "first"),
        Valor_Total=("Valor Total", "first"),
    )

    evolution_df = (
        orders_df.groupby(["Representante", "Mes"], dropna=False, as_index=False)
        .agg(Receita_Total=("Valor_Total", "sum"))
        .sort_values(["Representante", "Mes"])
    )

    return evolution_df
