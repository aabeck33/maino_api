"""Customer tab rendering functions."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.processing import SalesAnalytics
from dashboard.components import custom_table, metric_card


def render_customers(sales_df: pd.DataFrame) -> None:
    """Renders customer KPIs, chart and base table."""
    st.markdown("### 👥 Clientes")
    customer_summary_df = SalesAnalytics.get_customer_summary(sales_df)
    if customer_summary_df.empty:
        st.info("Nenhum cliente encontrado.")
        return

    customers_only_df = customer_summary_df[customer_summary_df["Distribuidor FDY"] != "Sim"]
    distributors_df = customer_summary_df[customer_summary_df["Distribuidor FDY"] == "Sim"]

    active_customers = customers_only_df["Cliente_Chave"].nunique()
    total_orders = customers_only_df["Pedidos"].sum()
    orders_per_customer = total_orders / active_customers if active_customers > 0 else 0
    active_distributors = distributors_df["Cliente_Chave"].nunique()
    distributor_orders = distributors_df["Pedidos"].sum()
    orders_per_distributor = distributor_orders / active_distributors if active_distributors > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Clientes Ativos", f"{active_customers:,}")
    with c2:
        metric_card("Pedidos por Cliente", f"{orders_per_customer:.2f}")
    with c3:
        metric_card("Distribuidores Ativos", f"{active_distributors:,}")
    with c4:
        metric_card("Pedidos por Distribuidor", f"{orders_per_distributor:.2f}")

    st.markdown("#### Top 10 Clientes por Quantidade de Pedidos")
    if customers_only_df.empty:
        st.info("Nenhum cliente (sem Distribuidor FDY) encontrado na seleção atual.")
    else:
        fig = px.bar(
            customers_only_df.head(10),
            x="Cliente_Chave",
            y="Pedidos",
            color="Pedidos",
            color_continuous_scale="Blues",
        )
        fig.update_layout(xaxis_title="Cliente", yaxis_title="Pedidos", height=450)
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Top 10 Distribuidores por Quantidade de Pedidos")
    if distributors_df.empty:
        st.info("Nenhum Distribuidor FDY encontrado na seleção atual.")
    else:
        dist_fig = px.bar(
            distributors_df.head(10),
            x="Cliente_Chave",
            y="Pedidos",
            color="Pedidos",
            color_continuous_scale="Greens",
        )
        dist_fig.update_layout(xaxis_title="Distribuidor", yaxis_title="Pedidos", height=450)
        st.plotly_chart(dist_fig, width="stretch")

    st.markdown("#### Base de Clientes")
    table_df = customer_summary_df[[
        "Cliente_Chave",
        "Distribuidor FDY",
        "Pedidos",
        "Receita_Total",
        "Ticket Médio",
    ]].copy()
    custom_table(
        table_df,
        columns_mapping={
            "Cliente_Chave": "Cliente",
            "Distribuidor FDY": "Distribuidor FDY",
            "Pedidos": "Pedidos",
            "Receita_Total": "Receita Total",
            "Ticket Médio": "Ticket Médio",
        },
    )
