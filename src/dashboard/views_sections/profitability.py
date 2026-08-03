"""Profitability tab rendering functions."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as ob
import streamlit as st
from plotly.subplots import make_subplots

from analytics.processing import SalesAnalytics
from dashboard.components import chart_container, chart_container_end, custom_table, metric_card
from dashboard.views_sections.common import format_currency, get_plot_layout


def render_profitability(
    sales_df: pd.DataFrame,
    profitability_df: Optional[pd.DataFrame],
    is_dark: bool,
    analytics: SalesAnalytics | None = None,
    profitability_artifacts: dict | None = None,
) -> None:
    """Renders the financial profitability dashboard section."""
    st.markdown("### Indicadores Financeiros e de Rentabilidade")

    if analytics is None:
        analytics = SalesAnalytics.__new__(SalesAnalytics)
        analytics.products_df = SalesAnalytics.load_products_catalog(None)

    analytics.df = sales_df

    if profitability_df is None or profitability_df.empty:
        profitability_df = analytics.build_profitability_dataset(sales_df)

    if profitability_artifacts is None:
        unified_revenue_total = analytics.calculate_total_revenue(sales_df)
        kpis = analytics.calculate_financial_kpis(
            profitability_df,
            revenue_total_override=unified_revenue_total,
        )
        product_summary_df = analytics.get_profitability_by_product(profitability_df)
        representative_summary_df = analytics.get_profitability_by_representative(profitability_df)
        customer_summary_df = analytics.get_profitability_by_customer(profitability_df)
        monthly_profitability_df = analytics.get_monthly_profitability(profitability_df)
        abc_revenue_df, _ = analytics.get_abc_analysis(product_summary_df, "Faturamento")
        abc_profit_df, _ = analytics.get_abc_analysis(product_summary_df, "Margem de contribuição")
    else:
        kpis = profitability_artifacts["financial_kpis"]
        product_summary_df = profitability_artifacts["product_profitability_df"]
        representative_summary_df = profitability_artifacts["representative_profitability_df"]
        customer_summary_df = profitability_artifacts["customer_profitability_df"]
        monthly_profitability_df = profitability_artifacts["monthly_profitability_df"]
        abc_revenue_df = profitability_artifacts["abc_revenue_df"]
        abc_profit_df = profitability_artifacts["abc_profit_df"]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        metric_card("Faturamento Total", format_currency(kpis["revenue_total"]), delta="Receita", delta_type="up")
    with c2:
        metric_card("Margem de contribuição", format_currency(kpis["gross_profit_total"]), delta="Resultado", delta_type="up")
    with c3:
        metric_card("Margem de Contribuição Média", f"{kpis['gross_margin_avg']:.2f}%", delta="Rentabilidade", delta_type="up")
    with c4:
        metric_card("Produto Mais Lucrativo", kpis["top_product"], delta="Top SKU")
    with c5:
        metric_card("Representante Mais Lucrativo", kpis["top_representative"], delta="Top Rep")
    with c6:
        metric_card("Cliente Mais Lucrativo", kpis["top_customer"], delta="Top Cliente")

    st.markdown("<br>", unsafe_allow_html=True)
    c7, c8 = st.columns(2)
    operational_profit_delta_type = "up" if kpis["estimated_operating_profit_value"] >= 0 else "down"
    operational_margin_delta_type = "up" if kpis["estimated_operating_profit_pct"] >= 0 else "down"
    with c7:
        metric_card(
            "Lucro Operacional Estimado",
            format_currency(kpis["estimated_operating_profit_value"]),
            delta=f"CF {kpis['fixed_cost_pct']:.2f}%",
            delta_type=operational_profit_delta_type,
        )
    with c8:
        metric_card(
            "Margem Operacional",
            f"{kpis['estimated_operating_profit_pct']:.2f}%",
            delta="Após Custos Fixos",
            delta_type=operational_margin_delta_type,
        )

    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)

    chart_container("Evolução Mensal de Faturamento, Lucro e Margem", "Comparativo financeiro pelo período analisado")
    if not monthly_profitability_df.empty:
        fig_monthly = make_subplots(specs=[[{"secondary_y": True}]])
        fig_monthly.add_trace(
            ob.Bar(x=monthly_profitability_df["Mês"], y=monthly_profitability_df["Faturamento"], name="Faturamento", marker_color="#2563eb", opacity=0.8),
            secondary_y=False,
        )
        fig_monthly.add_trace(
            ob.Scatter(x=monthly_profitability_df["Mês"], y=monthly_profitability_df["Margem de contribuição"], name="Margem de contribuição", line=dict(color="#22c55e", width=3)),
            secondary_y=False,
        )
        fig_monthly.add_trace(
            ob.Scatter(x=monthly_profitability_df["Mês"], y=monthly_profitability_df["Margem Bruta (%)"], name="Margem Bruta (%)", line=dict(color="#f59e0b", width=3)),
            secondary_y=True,
        )
        fig_monthly.update_layout(get_plot_layout(is_dark))
        fig_monthly.update_yaxes(title_text="R$", secondary_y=False)
        fig_monthly.update_yaxes(title_text="Margem (%)", secondary_y=True)
        st.plotly_chart(fig_monthly, width="stretch", config={"displayModeBar": False})
    else:
        st.info("Não há dados suficientes para montar a evolução mensal.")
    chart_container_end()

    chart_container("Comparativo Faturamento x Lucro", "Contribuição financeira dos principais produtos")
    if not product_summary_df.empty:
        compare_df = product_summary_df.head(10).copy().sort_values(["Faturamento", "Margem de contribuição"], ascending=True)
        fig_compare = make_subplots(specs=[[{"secondary_y": True}]])
        fig_compare.add_trace(
            ob.Bar(x=compare_df["Código do Produto"], y=compare_df["Faturamento"], name="Faturamento", marker_color="#2563eb", opacity=0.7),
            secondary_y=False,
        )
        fig_compare.add_trace(
            ob.Scatter(x=compare_df["Código do Produto"], y=compare_df["Margem de contribuição"], name="Margem de contribuição", line=dict(color="#22c55e", width=3)),
            secondary_y=True,
        )
        fig_compare.update_layout(get_plot_layout(is_dark))
        fig_compare.update_yaxes(title_text="R$", secondary_y=False)
        fig_compare.update_yaxes(title_text="Lucro (R$)", secondary_y=True)
        st.plotly_chart(fig_compare, width="stretch", config={"displayModeBar": False})
    chart_container_end()

    st.markdown("#### Rankings Financeiros")
    col1, col2 = st.columns(2)
    with col1:
        chart_container("Top 10 Produtos por Lucro", "Produtos que mais geram resultado financeiro")
        top_profit_df = product_summary_df.head(10).copy()
        if not top_profit_df.empty:
            top_profit_df = top_profit_df.sort_values("Margem de contribuição", ascending=True)
            fig_profit = px.bar(
                top_profit_df,
                x="Margem de contribuição",
                y="Código do Produto",
                orientation="h",
                labels={"Margem de contribuição": "Margem de contribuição (R$)", "Código do Produto": "Produto"},
                color="Margem de contribuição",
                color_continuous_scale="Greens",
                text_auto=",.0f",
            )
            fig_profit.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_profit, width="stretch", config={"displayModeBar": False})
        chart_container_end()

    with col2:
        chart_container("Top 10 Produtos por Receita", "Produtos com maior faturamento")
        top_revenue_df = product_summary_df.head(10).copy()
        if not top_revenue_df.empty:
            top_revenue_df = top_revenue_df.sort_values("Faturamento", ascending=True)
            fig_revenue = px.bar(
                top_revenue_df,
                x="Faturamento",
                y="Código do Produto",
                orientation="h",
                labels={"Faturamento": "Faturamento (R$)", "Código do Produto": "Produto"},
                color="Faturamento",
                color_continuous_scale="Blues",
                text_auto=",.0f",
            )
            fig_revenue.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_revenue, width="stretch", config={"displayModeBar": False})
        chart_container_end()

    st.markdown("#### Curvas ABC Financeiras")
    col_abc_revenue, col_abc_profit = st.columns(2)
    with col_abc_revenue:
        chart_container("Curva ABC por Receita", "Classificação dos produtos pelo impacto no faturamento")
        if not abc_revenue_df.empty:
            fig_abc_revenue = px.bar(
                abc_revenue_df.head(15),
                x="Código do Produto",
                y="Faturamento",
                color="Classe ABC",
                labels={"Código do Produto": "Produto", "Faturamento": "Receita (R$)"},
                color_discrete_map={"A": "#2563eb", "B": "#f59e0b", "C": "#16a34a"},
            )
            fig_abc_revenue.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_abc_revenue, width="stretch", config={"displayModeBar": False})
        chart_container_end()

    with col_abc_profit:
        chart_container("Curva ABC por Lucro", "Classificação dos produtos pela contribuição para o lucro")
        if not abc_profit_df.empty:
            fig_abc_profit = px.bar(
                abc_profit_df.head(15),
                x="Código do Produto",
                y="Margem de contribuição",
                color="Classe ABC",
                labels={"Código do Produto": "Produto", "Margem de contribuição": "Margem de contribuição (R$)"},
                color_discrete_map={"A": "#2563eb", "B": "#f59e0b", "C": "#16a34a"},
            )
            fig_abc_profit.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_abc_profit, width="stretch", config={"displayModeBar": False})
        chart_container_end()

    st.markdown("#### Tabelas de Análise")
    c_table1, c_table2, c_table3 = st.columns(3)
    with c_table1:
        st.markdown("**Top 10 Produtos por Lucro**")
        custom_table(
            product_summary_df.head(10)[["Código do Produto", "Faturamento", "Margem de contribuição", "Margem Bruta (%)", "Participação no Lucro (%)"]],
            columns_mapping={
                "Código do Produto": "Produto",
                "Faturamento": "Faturamento",
                "Margem de contribuição": "Margem de contribuição",
                "Margem Bruta (%)": "Margem Bruta (%)",
                "Participação no Lucro (%)": "% Lucro",
            },
        )
    with c_table2:
        st.markdown("**Representantes por Lucro**")
        custom_table(
            representative_summary_df[["Representante", "Faturamento", "Margem de contribuição", "Margem Bruta (%)"]],
            columns_mapping={
                "Representante": "Representante",
                "Faturamento": "Faturamento",
                "Margem de contribuição": "Margem de contribuição",
                "Margem Bruta (%)": "Margem Bruta (%)",
            },
        )
    with c_table3:
        st.markdown("**Clientes Mais Lucrativos**")
        custom_table(
            customer_summary_df[["Cliente", "Faturamento", "Margem de contribuição", "Margem Bruta (%)"]],
            columns_mapping={
                "Cliente": "Cliente",
                "Faturamento": "Faturamento",
                "Margem de contribuição": "Margem de contribuição",
                "Margem Bruta (%)": "Margem Bruta (%)",
            },
        )
