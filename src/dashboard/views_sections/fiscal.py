"""Fiscal tab rendering functions."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as ob
import streamlit as st

from analytics.processing import SalesAnalytics
from dashboard.components import chart_container, chart_container_end, metric_card
from dashboard.views_sections.common import get_plot_layout


def render_fiscal(sales_df: pd.DataFrame, is_dark: bool) -> None:
    """Renders the fiscal status and invoice compliance tab."""
    st.markdown("### Painel de Conformidade Fiscal")

    kpis = SalesAnalytics.calculate_kpis(sales_df)

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Pedidos com Nota Fiscal", f"{kpis['orders_with_nf']}", delta="Faturamento Fiscal")
    with c2:
        metric_card(
            "Pedidos sem Nota Fiscal",
            f"{kpis['orders_without_nf']}",
            delta="Pendente",
            delta_type="warn" if kpis["orders_without_nf"] > 0 else "up",
        )
    with c3:
        metric_card(
            "Taxa de Emissão de NF",
            f"{kpis['nf_emission_rate']:.1f}%",
            delta="Compliance",
            delta_type="up" if kpis["nf_emission_rate"] > 80 else "warn",
        )

    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    col_gauge, col_donut = st.columns(2)

    with col_gauge:
        chart_container("Taxa de Cobertura Fiscal (Emissão)", "Percentual de pedidos com nota fiscal transmitida")
        fig_gauge = ob.Figure(
            ob.Indicator(
                mode="gauge+number",
                value=kpis["nf_emission_rate"],
                domain={"x": [0, 1], "y": [0, 1]},
                number={"suffix": "%", "font": {"size": 40}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "gray"},
                    "bar": {"color": "#2563eb"},
                    "bgcolor": "rgba(0,0,0,0)",
                    "borderwidth": 2,
                    "bordercolor": "#1e1e24" if is_dark else "#e4e4e7",
                    "steps": [
                        {"range": [0, 50], "color": "rgba(239,68,68,0.1)"},
                        {"range": [50, 85], "color": "rgba(245,158,11,0.1)"},
                        {"range": [85, 100], "color": "rgba(34,197,94,0.1)"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90,
                    },
                },
            )
        )
        fig_gauge.update_layout(get_plot_layout(is_dark))
        fig_gauge.update_layout(height=260, margin=dict(l=30, r=30, t=40, b=10))
        st.plotly_chart(fig_gauge, width="stretch", config={"displayModeBar": False})
        chart_container_end()

    with col_donut:
        chart_container("Distribuição por Status das NF", "Quantidade de pedidos por status de faturamento")
        fiscal_distribution_df = SalesAnalytics.get_fiscal_distribution(sales_df)
        if not fiscal_distribution_df.empty:
            fig_donut = px.pie(
                fiscal_distribution_df,
                values="Quantidade",
                names="Status da Nota Fiscal",
                hole=0.5,
                color="Status da Nota Fiscal",
                color_discrete_map={
                    "ACEITA": "#16a34a",
                    "Não emitida": "#ef4444",
                    "DENEGADA": "#f59e0b",
                    "REJEITADA": "#dc2626",
                },
            )
            fig_donut.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_donut, width="stretch", config={"displayModeBar": False})
        chart_container_end()
