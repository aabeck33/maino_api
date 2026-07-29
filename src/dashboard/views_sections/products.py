"""Product and order tab rendering functions."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as ob
import streamlit as st
from plotly.subplots import make_subplots

from analytics.processing import SalesAnalytics
from dashboard.components import chart_container, chart_container_end, custom_table, metric_card
from dashboard.views_sections.common import get_plot_layout


def render_products(sales_df: pd.DataFrame, is_dark: bool) -> None:
    """Renders product analytics including ranking, Pareto and ABC."""
    st.markdown("### Análise de Produtos")

    unique_products = int(sales_df["Código do Produto"].astype(str).nunique()) if "Código do Produto" in sales_df.columns else 0
    metric_card("Produtos Únicos Comercializados", f"{unique_products:,}", delta="Portfólio Ativo", delta_type="up")
    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)

    chart_container("Ranking de Produtos Mais Vendidos", "Selecione o limite de exibição")
    limit = st.radio("Quantidade de itens no ranking:", [10, 20], horizontal=True)

    products_abc_df, class_counts = SalesAnalytics.get_abc_pareto_analysis(sales_df)

    if not products_abc_df.empty:
        top_products_df = products_abc_df.head(limit).copy().sort_values(by="Quantidade", ascending=True)
        fig_top = px.bar(
            top_products_df,
            x="Quantidade",
            y="Código do Produto",
            orientation="h",
            labels={"Quantidade": "Volume Vendido", "Código do Produto": "Produto"},
            color_discrete_sequence=["#2563eb"],
        )
        fig_top.update_layout(get_plot_layout(is_dark))
        fig_top.update_layout(margin=dict(l=100, r=40, t=10, b=40))
        st.plotly_chart(fig_top, width="stretch", config={"displayModeBar": False})
    chart_container_end()

    if not products_abc_df.empty:
        chart_container("Gráfico de Pareto (Regra 80/20)", "Participação individual de vendas vs volume acumulado")
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pareto.add_trace(
            ob.Bar(
                x=products_abc_df["Código do Produto"],
                y=products_abc_df["Quantidade"],
                name="Qtd Vendida",
                marker_color="#2563eb",
                opacity=0.85,
            ),
            secondary_y=False,
        )
        fig_pareto.add_trace(
            ob.Scatter(
                x=products_abc_df["Código do Produto"],
                y=products_abc_df["Acumulado (%)"],
                name="% Acumulado",
                line=dict(color="#d97706", width=3),
                mode="lines+markers",
            ),
            secondary_y=True,
        )

        fig_pareto.update_layout(get_plot_layout(is_dark))
        fig_pareto.update_yaxes(title_text="Quantidade (Itens)", secondary_y=False)
        fig_pareto.update_yaxes(title_text="Percentual Acumulado (%)", range=[0, 105], secondary_y=True)
        fig_pareto.update_xaxes(title_text="Produtos")
        st.plotly_chart(fig_pareto, width="stretch", config={"displayModeBar": False})
        chart_container_end()

    st.markdown("#### Curva ABC (Classificação de Estoque)")
    col_abc_chart, col_abc_table = st.columns([1, 1])

    with col_abc_chart:
        chart_container("Distribuição por Classe ABC", "Participação de itens em cada faixa de faturamento físico")

        abc_distribution_df = pd.DataFrame({
            "Classe": list(class_counts.keys()),
            "Qtd Produtos": list(class_counts.values()),
        })

        total_items = abc_distribution_df["Qtd Produtos"].sum()
        abc_distribution_df["Participação (%)"] = (
            abc_distribution_df["Qtd Produtos"] / total_items * 100
            if total_items > 0
            else 0.0
        )

        fig_abc = px.bar(
            abc_distribution_df,
            x="Classe",
            y="Qtd Produtos",
            text="Qtd Produtos",
            color="Classe",
            color_discrete_map={"A": "#2563eb", "B": "#f59e0b", "C": "#16a34a"},
            labels={"Qtd Produtos": "Quantidade de SKU", "Classe": "Classe ABC"},
        )
        fig_abc.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_abc, width="stretch", config={"displayModeBar": False})
        chart_container_end()

    with col_abc_table:
        st.markdown("##### Produtos Classificados")
        custom_table(
            products_abc_df[["Código do Produto", "Quantidade", "Classe ABC"]],
            columns_mapping={
                "Código do Produto": "Código do Produto",
                "Quantidade": "Qtd Total Vendida",
                "Classe ABC": "Classe",
            },
        )


def render_orders(sales_df: pd.DataFrame, is_dark: bool) -> None:
    """Renders order distribution and outlier analysis."""
    st.markdown("### Análise de Pedidos")

    order_stats, largest_orders_df = SalesAnalytics.get_order_stats(sales_df)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Média de Itens/Pedido", f"{order_stats['mean']:.1f}", delta="Volume Médio")
    with c2:
        metric_card("Mediana de Itens/Pedido", f"{order_stats['median']:.1f}", delta="Mediana Real")
    with c3:
        metric_card("Volume Máximo em Pedido", f"{int(order_stats['max']):,}", delta="Maior Pedido", delta_type="up")
    with c4:
        metric_card("Volume Mínimo em Pedido", f"{int(order_stats['min']):,}", delta="Menor Pedido")

    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

    col_hist, col_box = st.columns(2)

    with col_hist:
        chart_container("Distribuição de Volumes dos Pedidos", "Frequência de pedidos por faixa de quantidade de itens")
        if not largest_orders_df.empty:
            fig_hist = px.histogram(
                largest_orders_df,
                x="Quantidade",
                nbins=20,
                labels={"Quantidade": "Quantidade de Itens por Pedido", "count": "Frequência"},
                color_discrete_sequence=["#2563eb"],
            )
            fig_hist.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_hist, width="stretch", config={"displayModeBar": False})
        chart_container_end()

    with col_box:
        chart_container("Dispersão e Outliers de Volumes", "Visualização de quartis e valores discrepantes (box plot)")
        if not largest_orders_df.empty:
            fig_box = px.box(
                largest_orders_df,
                y="Quantidade",
                labels={"Quantidade": "Itens por Pedido"},
                color_discrete_sequence=["#d97706"],
            )
            fig_box.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_box, width="stretch", config={"displayModeBar": False})
        chart_container_end()

    st.markdown("#### Ranking de Pedidos de Maior Volume")
    if not largest_orders_df.empty:
        col_tab, col_info = st.columns([2, 1])
        with col_tab:
            custom_table(
                largest_orders_df.head(10),
                columns_mapping={
                    "Pedido ID": "Pedido ID",
                    "Número do Pedido": "Número do Pedido",
                    "Quantidade": "Volume Total (Itens)",
                },
            )
        with col_info:
            st.markdown(
                """
            <div class="insight-card">
                <div class="insight-title">Análise de Concentração</div>
                <div class="insight-desc">
                    Identificar os maiores pedidos ajuda a monitorar os clientes mais valiosos
                    e prever a necessidade de logística especial ou negociações comerciais dedicadas.
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
