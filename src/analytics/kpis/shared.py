"""Shared helpers for KPI calculations."""

from __future__ import annotations

from typing import Any
import pandas as pd


def coerce_customer_key(sales_df: pd.DataFrame) -> pd.Series:
    """Builds a resilient customer key from available columns."""
    if sales_df.empty:
        return pd.Series(dtype="object")
    if "Cliente" in sales_df.columns:
        raw_series = sales_df["Cliente"]
    elif "Nome do Cliente" in sales_df.columns:
        raw_series = sales_df["Nome do Cliente"]
    elif "CPF/CNPJ do Cliente" in sales_df.columns:
        raw_series = sales_df["CPF/CNPJ do Cliente"]
    elif "Pedido ID" in sales_df.columns:
        raw_series = sales_df["Pedido ID"]
    else:
        raw_series = pd.Series(["N/A"] * len(sales_df), index=sales_df.index)

    return raw_series.astype(str).str.strip().replace({"": "N/A"}).fillna("N/A")


def safe_rate(numerator: float, denominator: float) -> float:
    """Calculates a percentage safely for KPI computations."""
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100.0


def normalize_value(value: Any) -> str:
    """Normalizes arbitrary values for textual KPI comparisons."""
    if value is None:
        return ""
    return str(value).strip()
