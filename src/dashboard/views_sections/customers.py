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

    active_customers = customer_summary_df["Cliente_Chave"].nunique()
    total_orders = customer_summary_df["Pedidos"].sum()
    orders_per_customer = total_orders / active_customers if active_customers > 0 else 0

    c1, c2 = st.columns(2)
    with c1:
        metric_card("Clientes Ativos", f"{active_customers:,}")
    with c2:
        metric_card("Pedidos por Cliente", f"{orders_per_customer:.2f}")

    st.markdown("#### Top 10 Clientes por Quantidade de Pedidos")
    fig = px.bar(
        customer_summary_df.head(10),
        x="Cliente_Chave",
        y="Pedidos",
        color="Pedidos",
        color_continuous_scale="Blues",
    )
    fig.update_layout(xaxis_title="Cliente", yaxis_title="Pedidos", height=450)
    st.plotly_chart(fig, width="stretch")

    st.markdown("#### Base de Clientes")
    custom_table(
        customer_summary_df,
        columns_mapping={
            "Cliente_Chave": "Cliente",
            "Pedidos": "Pedidos",
            "Receita_Total": "Receita Total",
            "Ticket Médio": "Ticket Médio",
        },
    )
