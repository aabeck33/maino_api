"""Profitability KPI calculations and financial summaries."""

from __future__ import annotations

import os
from typing import Any
import pandas as pd
import logging

from analytics.kpis.shared import coerce_customer_key, revenue_series, total_revenue
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _get_variable_cost_percentage(origin: str | None) -> float:
    """Returns variable cost percentage according to product origin."""
    if origin is None:
        return float(os.getenv("CUSTO_VARIAVEL_NACIONAL", "0.2615"))

    normalized_origin = str(origin).strip().lower()
    if "estrangeira" in normalized_origin or "import" in normalized_origin:
        if "mercado interno" in normalized_origin or "mercado nacional" in normalized_origin or "adquirida" in normalized_origin:
            return float(os.getenv("CUSTO_VARIAVEL_NACIONAL", "0.2615"))
        return float(os.getenv("CUSTO_VARIAVEL_IMPORTADO", "0.2015"))

    return float(os.getenv("CUSTO_VARIAVEL_NACIONAL", "0.2615"))


def _build_order_based_revenue(profitability_df: pd.DataFrame) -> pd.Series:
    """Builds line-level revenue from item totals.

    In consolidated dataset, ``Valor Total`` is line-level (unit price * quantity),
    so profitability should preserve it directly per row.
    """
    if "Valor Total" not in profitability_df.columns:
        reference_price = pd.to_numeric(
            profitability_df.get("Preço de Venda", pd.Series(0.0, index=profitability_df.index, dtype="float64")),
            errors="coerce",
        ).fillna(0.0)
        quantity = pd.to_numeric(
            profitability_df.get("Quantidade", pd.Series(0.0, index=profitability_df.index, dtype="float64")),
            errors="coerce",
        ).fillna(0.0)
        return reference_price * quantity
    return revenue_series(profitability_df, value_column="Valor Total")


def build_profitability_dataset(sales_df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    """Builds item-level profitability dataset as single source of truth.

    Formula
    -------
    Faturamento = Valor Total do Item
    Custo Total = (PU de entrada * Quantidade) + (Faturamento * Custo Variável %)
    Margem de contribuição = Faturamento - Custo Total
    Margem Bruta (%) = Margem de contribuição / Faturamento * 100

    Parameters
    ----------
    sales_df : pd.DataFrame
        Sales rows after filtering.
    products_df : pd.DataFrame
        Products catalog with cost and price information.

    Returns
    -------
    pd.DataFrame
        Profitability base used by dashboard and PDF.
    """
    if sales_df.empty:
        return pd.DataFrame(columns=[
            "Código do Produto",
            "Descrição do Produto",
            "Quantidade",
            "Faturamento",
            "Custo Total",
            "Margem de contribuição",
            "Margem Bruta (%)",
            "Representante",
            "Cliente",
            "UF",
        ])

    profitability_df = sales_df.copy()
    profitability_df["Quantidade"] = pd.to_numeric(profitability_df["Quantidade"], errors="coerce").fillna(0.0)
    profitability_df["Código do Produto"] = profitability_df["Código do Produto"].astype(str).str.strip().str.upper()
    profitability_df["Cliente"] = coerce_customer_key(profitability_df)
    profitability_df["Representante"] = (
        profitability_df.get("Representante", pd.Series(["N/A"] * len(profitability_df), index=profitability_df.index))
        .astype(str)
        .str.strip()
        .replace({"": "N/A"})
        .fillna("N/A")
    )
    profitability_df["UF"] = (
        profitability_df.get("UF", pd.Series(["N/A"] * len(profitability_df), index=profitability_df.index))
        .astype(str)
        .str.strip()
        .str.upper()
        .replace({"": "N/A"})
        .fillna("N/A")
    )

    normalized_products_df = products_df.copy()
    if normalized_products_df.empty:
        normalized_products_df = pd.DataFrame({"Código": [], "Descrição": [], "PU de entrada": [], "PU de saída": [], "Origem": []})

    normalized_products_df["Código"] = normalized_products_df.get("Código", "").astype(str).str.strip().str.upper()
    normalized_products_df["Descrição"] = normalized_products_df.get("Descrição", pd.Series(["N/A"] * len(normalized_products_df), index=normalized_products_df.index)).astype(str)
    normalized_products_df["Origem"] = normalized_products_df.get("Origem", pd.Series([""] * len(normalized_products_df), index=normalized_products_df.index)).astype(str)

    for price_column in ["PU de entrada", "PU de saída"]:
        normalized_products_df[price_column] = pd.to_numeric(
            normalized_products_df.get(price_column, 0.0),
            errors="coerce",
        ).fillna(0.0)

    profitability_df = profitability_df.merge(
        normalized_products_df[["Código", "Descrição", "PU de entrada", "PU de saída", "Origem"]].rename(
            columns={"Código": "Código do Produto", "Descrição": "Descrição do Produto"}
        ),
        on="Código do Produto",
        how="left",
    )

    custo = pd.to_numeric(
        profitability_df.get("Custo", pd.Series(0.0, index=profitability_df.index, dtype="float64")),
        errors="coerce",
    )
    pu_entrada = pd.to_numeric(
        profitability_df.get("PU de entrada", pd.Series(0.0, index=profitability_df.index, dtype="float64")),
        errors="coerce",
    )
    profitability_df["Preço de Entrada"] = (custo.where(custo > 0, pu_entrada).fillna(0.0))
    logger.debug(
        "Usando custo real: %s registros",
        (custo > 0).sum()
    )
    logger.debug(
        "Usando PU de entrada: %s registros",
        (custo <= 0).sum()
    )
    profitability_df["Preço de Venda"] = pd.to_numeric(
        profitability_df.get("PU de saída", pd.Series(0.0, index=profitability_df.index, dtype="float64")),
        errors="coerce",
    ).fillna(0.0)
    profitability_df["Origem"] = profitability_df.get("Origem", "").astype(str).fillna("")

    profitability_df["Faturamento"] = _build_order_based_revenue(profitability_df)
    profitability_df["Custo Variável (%)"] = profitability_df["Origem"].apply(_get_variable_cost_percentage)
    profitability_df["Custo Total"] = (
        profitability_df["Preço de Entrada"] * profitability_df["Quantidade"]
        + profitability_df["Faturamento"] * profitability_df["Custo Variável (%)"]
    )

    profitability_df["Margem de contribuição"] = profitability_df["Faturamento"] - profitability_df["Custo Total"]
    profitability_df["Lucro Bruto"] = profitability_df["Margem de contribuição"]
    profitability_df["Margem Bruta (%)"] = 0.0

    non_zero_revenue_mask = profitability_df["Faturamento"] > 0
    profitability_df.loc[non_zero_revenue_mask, "Margem Bruta (%)"] = (
        profitability_df.loc[non_zero_revenue_mask, "Margem de contribuição"]
        / profitability_df.loc[non_zero_revenue_mask, "Faturamento"]
        * 100
    )

    default_rep = os.getenv("NOME_PADRAO_REPRESENTANTE", "").strip()
    if not default_rep or default_rep.upper() in {"N/A", "NA", "NONE", "NULL", "<NA>"}:
        default_rep = "Sem Representante"

    profitability_df["Representante"] = profitability_df["Representante"].astype(str).str.strip()
    missing_rep_mask = profitability_df["Representante"].isin(["", "N/A", "NA", "None", "none", "nan", "NaN", "<NA>"])
    profitability_df.loc[missing_rep_mask, "Representante"] = default_rep
    profitability_df["Representante"] = profitability_df["Representante"].replace({"": default_rep}).fillna(default_rep)
    profitability_df["Descrição do Produto"] = profitability_df["Descrição do Produto"].fillna("N/A")

    return profitability_df


def calculate_financial_kpis(
    profitability_df: pd.DataFrame,
    fixed_cost_pct: float,
    revenue_total_override: float | None = None,
) -> dict[str, Any]:
    """Calculates financial KPIs from profitability base."""
    normalized_fixed_cost_pct = float(fixed_cost_pct)
    if abs(normalized_fixed_cost_pct) <= 1.0:
        normalized_fixed_cost_pct *= 100.0

    if profitability_df.empty:
        return {
            "revenue_total": 0.0,
            "gross_profit_total": 0.0,
            "gross_margin_avg": 0.0,
            "top_product": "N/A",
            "top_representative": "N/A",
            "top_customer": "N/A",
            "fixed_cost_pct": normalized_fixed_cost_pct,
            "fixed_cost_value": 0.0,
            "estimated_operating_profit_pct": 0.0,
            "estimated_operating_profit_value": 0.0,
        }

    revenue_total = float(revenue_total_override) if revenue_total_override is not None else total_revenue(profitability_df, value_column="Faturamento")
    gross_profit_total = float(profitability_df["Margem de contribuição"].sum())
    gross_margin_avg = (gross_profit_total / revenue_total * 100) if revenue_total > 0 else 0.0

    product_summary_df = summarize_profitability_by_product(profitability_df)
    rep_summary_df = summarize_profitability_by_representative(profitability_df)
    customer_summary_df = summarize_profitability_by_customer(profitability_df)

    top_product = product_summary_df.iloc[0]["Código do Produto"] if not product_summary_df.empty else "N/A"
    top_representative = rep_summary_df.iloc[0]["Representante"] if not rep_summary_df.empty else "N/A"
    top_customer = customer_summary_df.iloc[0]["Cliente"] if not customer_summary_df.empty else "N/A"

    fixed_cost_value = revenue_total * normalized_fixed_cost_pct / 100
    estimated_operating_profit_value = gross_profit_total - fixed_cost_value
    estimated_operating_profit_pct = (estimated_operating_profit_value / revenue_total * 100) if revenue_total > 0 else 0.0

    logger.debug("fixed_cost_value = revenue_total * normalized_fixed_cost_pct / 100: %s * %s = %s", revenue_total, normalized_fixed_cost_pct, fixed_cost_value)
    logger.debug("estimated_operating_profit_value = gross_profit_total - fixed_cost_value: %s - %s = %s", gross_profit_total, fixed_cost_value, estimated_operating_profit_value)
    logger.debug("estimated_operating_profit_pct = (estimated_operating_profit_value / revenue_total * 100): %s / %s * 100 = %s", estimated_operating_profit_value, revenue_total, estimated_operating_profit_pct)

    return {
        "revenue_total": revenue_total,
        "gross_profit_total": gross_profit_total,
        "gross_margin_avg": gross_margin_avg,
        "top_product": top_product,
        "top_representative": top_representative,
        "top_customer": top_customer,
        "fixed_cost_pct": normalized_fixed_cost_pct,
        "fixed_cost_value": fixed_cost_value,
        "estimated_operating_profit_pct": estimated_operating_profit_pct,
        "estimated_operating_profit_value": estimated_operating_profit_value,
    }


def summarize_profitability_by_product(profitability_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates profitability metrics by product."""
    if profitability_df.empty:
        return pd.DataFrame(columns=["Código do Produto", "Descrição do Produto", "Faturamento", "Margem de contribuição", "Margem Bruta (%)", "Quantidade", "Participação no Lucro (%)", "Participação no Faturamento (%)"])

    summary_df = (
        profitability_df.groupby(["Código do Produto", "Descrição do Produto"], dropna=False, as_index=False)
        .agg(
            Quantidade=("Quantidade", "sum"),
            Faturamento=("Faturamento", "sum"),
            Lucro_Bruto=("Margem de contribuição", "sum"),
            Custo_Total=("Custo Total", "sum"),
        )
        .rename(columns={"Lucro_Bruto": "Margem de contribuição"})
    )

    summary_df["Margem Bruta (%)"] = 0.0
    non_zero_mask = summary_df["Faturamento"] > 0
    summary_df.loc[non_zero_mask, "Margem Bruta (%)"] = (
        summary_df.loc[non_zero_mask, "Margem de contribuição"] / summary_df.loc[non_zero_mask, "Faturamento"] * 100
    )

    total_profit = summary_df["Margem de contribuição"].sum()
    total_revenue = summary_df["Faturamento"].sum()
    summary_df["Participação no Lucro (%)"] = (summary_df["Margem de contribuição"] / total_profit * 100) if total_profit > 0 else 0.0
    summary_df["Participação no Faturamento (%)"] = (summary_df["Faturamento"] / total_revenue * 100) if total_revenue > 0 else 0.0

    return summary_df.sort_values("Margem de contribuição", ascending=False).reset_index(drop=True)


def summarize_profitability_by_representative(profitability_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates profitability metrics by representative."""
    if profitability_df.empty:
        return pd.DataFrame(columns=["Representante", "Faturamento", "Margem de contribuição", "Margem Bruta (%)"])

    summary_df = (
        profitability_df.groupby("Representante", dropna=False, as_index=False)
        .agg(Faturamento=("Faturamento", "sum"), Lucro_Bruto=("Margem de contribuição", "sum"))
        .rename(columns={"Lucro_Bruto": "Margem de contribuição"})
    )
    summary_df["Margem Bruta (%)"] = 0.0
    non_zero_mask = summary_df["Faturamento"] > 0
    summary_df.loc[non_zero_mask, "Margem Bruta (%)"] = (
        summary_df.loc[non_zero_mask, "Margem de contribuição"] / summary_df.loc[non_zero_mask, "Faturamento"] * 100
    )

    return summary_df.sort_values("Margem de contribuição", ascending=False).reset_index(drop=True)


def summarize_profitability_by_customer(profitability_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates profitability metrics by customer."""
    if profitability_df.empty:
        return pd.DataFrame(columns=["Cliente", "Faturamento", "Margem de contribuição", "Margem Bruta (%)"])

    summary_df = (
        profitability_df.groupby("Cliente", dropna=False, as_index=False)
        .agg(Faturamento=("Faturamento", "sum"), Lucro_Bruto=("Margem de contribuição", "sum"))
        .rename(columns={"Lucro_Bruto": "Margem de contribuição"})
    )
    summary_df["Margem Bruta (%)"] = 0.0
    non_zero_mask = summary_df["Faturamento"] > 0
    summary_df.loc[non_zero_mask, "Margem Bruta (%)"] = (
        summary_df.loc[non_zero_mask, "Margem de contribuição"] / summary_df.loc[non_zero_mask, "Faturamento"] * 100
    )

    return summary_df.sort_values("Margem de contribuição", ascending=False).reset_index(drop=True)


def summarize_monthly_profitability(profitability_df: pd.DataFrame, date_column: str | None) -> pd.DataFrame:
    """Builds monthly financial evolution using a resolved date column."""
    if profitability_df.empty:
        return pd.DataFrame(columns=["Mês", "Faturamento", "Margem de contribuição", "Margem Bruta (%)"])

    monthly_df = profitability_df.copy()

    if date_column and date_column in monthly_df.columns:
        monthly_df[date_column] = pd.to_datetime(monthly_df[date_column], errors="coerce")
        monthly_df = monthly_df[monthly_df[date_column].notna()]
        if monthly_df.empty:
            monthly_df["Mês"] = pd.Timestamp.today().to_period("M").to_timestamp()
        else:
            monthly_df["Mês"] = monthly_df[date_column].dt.to_period("M").dt.to_timestamp()
    else:
        monthly_df["Mês"] = pd.Timestamp.today().to_period("M").to_timestamp()

    monthly_summary_df = (
        monthly_df.groupby("Mês", dropna=False, as_index=False)
        .agg(Faturamento=("Faturamento", "sum"), Lucro_Bruto=("Margem de contribuição", "sum"))
        .rename(columns={"Lucro_Bruto": "Margem de contribuição"})
    )

    monthly_summary_df["Margem Bruta (%)"] = 0.0
    non_zero_mask = monthly_summary_df["Faturamento"] > 0
    monthly_summary_df.loc[non_zero_mask, "Margem Bruta (%)"] = (
        monthly_summary_df.loc[non_zero_mask, "Margem de contribuição"] / monthly_summary_df.loc[non_zero_mask, "Faturamento"] * 100
    )

    return monthly_summary_df.sort_values("Mês").reset_index(drop=True)
