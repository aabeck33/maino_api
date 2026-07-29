"""Representative tab rendering functions."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.processing import SalesAnalytics
from dashboard.components import chart_container, chart_container_end, custom_table, metric_card
from dashboard.views_sections.common import get_plot_layout


def render_representatives(sales_df: pd.DataFrame, is_dark: bool) -> None:
    """Renders the sales representatives performance tab."""
    st.markdown("### Representantes de Vendas")

    summary_df = SalesAnalytics.get_representative_performance(sales_df)
    monthly_evolution_df = SalesAnalytics.get_representative_monthly_evolution(sales_df)

    expected_columns = [
        "Representante",
        "Receita_Total",
        "Clientes_Unicos",
        "Pedidos",
        "Ticket_Medio",
        "Pedidos_por_Cliente",
        "Participacao (%)",
        "Produtos_Distintos",
    ]
    for column in expected_columns:
        if column not in summary_df.columns:
            summary_df[column] = 0 if column != "Representante" else "N/A"

    summary_df = summary_df.sort_values(by="Receita_Total", ascending=False).reset_index(drop=True)
    total_clients = summary_df["Clientes_Unicos"].sum()
    total_orders = summary_df["Pedidos"].sum()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Representantes Ativos", f"{len(summary_df):,}", delta="Força Comercial")
    with c2:
        metric_card("Clientes Atendidos", f"{total_clients:,}", delta="Clientes Únicos")
    with c3:
        metric_card("Pedidos Totais", f"{total_orders:,}", delta="Pedidos")
    with c4:
        max_mix = int(summary_df["Produtos_Distintos"].max()) if not summary_df.empty else 0
        metric_card("Maior Mix por Representantes", f"{max_mix:,}", delta="SKU distintos")

    if summary_df.empty:
        st.info("Nenhum dado de representantes para os filtros selecionados.")
        chart_container("Evolução Mensal de Vendas por Representante", "Tendência temporal de receita por representante")
        if not monthly_evolution_df.empty:
            fig_evolution = px.line(
                monthly_evolution_df,
                x="Mes",
                y="Receita_Total",
                color="Representante",
                markers=True,
                labels={"Mes": "Mês", "Receita_Total": "Receita (R$)"},
            )
            fig_evolution.update_layout(get_plot_layout(is_dark), margin=dict(l=40, r=40, t=30, b=40))
            st.plotly_chart(fig_evolution, width="stretch", config={"displayModeBar": False})
        else:
            st.info("Não foi possível gerar a evolução mensal porque não há coluna de data reconhecida no conjunto de dados.")
        chart_container_end()
        return

    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
    top_rep = summary_df.iloc[0]
    st.markdown(
        f"**Melhor Representante:** {top_rep['Representante']} com faturamento de R$ {top_rep['Receita_Total']:,.2f} ({top_rep['Participacao (%)']:.1f}%)"
    )

    chart_container("Ranking de Representantes por Faturamento", "Comparativo de receita por representante")
    fig_rank = px.bar(
        summary_df,
        x="Receita_Total",
        y="Representante",
        orientation="h",
        text="Receita_Total",
        labels={"Receita_Total": "Faturamento (R$)", "Representante": "Representante"},
        color="Participacao (%)",
        color_continuous_scale="Blues",
    )
    fig_rank.update_traces(texttemplate="R$ %{x:,.0f}", textposition="outside")
    fig_rank.update_layout(get_plot_layout(is_dark), margin=dict(l=120, r=40, t=30, b=40), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_rank, width="stretch", config={"displayModeBar": False})
    chart_container_end()

    st.markdown("#### Indicadores por Representante")
    table_columns = [
        "Representante",
        "Receita_Total",
        "Clientes_Unicos",
        "Pedidos",
        "Ticket_Medio",
        "Pedidos_por_Cliente",
        "Participacao (%)",
        "Produtos_Distintos",
    ]
    if "Atingimento (%)" in summary_df.columns:
        table_columns.append("Atingimento (%)")

    custom_table(
        summary_df[table_columns].rename(
            columns={
                "Receita_Total": "Receita Total",
                "Clientes_Unicos": "Clientes Atendidos",
                "Pedidos": "Pedidos",
                "Ticket_Medio": "Ticket Médio",
                "Pedidos_por_Cliente": "Pedidos por Cliente",
                "Participacao (%)": "% Participação",
                "Produtos_Distintos": "Produtos Distintos",
                "Atingimento (%)": "% Atingimento",
            }
        ),
        {
            "Representante": "Representante",
            "Receita Total": "Receita Total",
            "Clientes Atendidos": "Clientes Atendidos",
            "Pedidos": "Pedidos",
            "Ticket Médio": "Ticket Médio",
            "Pedidos por Cliente": "Pedidos por Cliente",
            "% Participação": "% Participação",
            "Produtos Distintos": "Produtos Distintos",
            "% Atingimento": "% Atingimento",
        },
    )

    chart_container("Evolução Mensal de Vendas por Representante", "Tendência temporal de receita por representante")
    if not monthly_evolution_df.empty:
        fig_evolution = px.line(
            monthly_evolution_df,
            x="Mes",
            y="Receita_Total",
            color="Representante",
            markers=True,
            labels={"Mes": "Mês", "Receita_Total": "Receita (R$)"},
        )
        fig_evolution.update_layout(get_plot_layout(is_dark), margin=dict(l=40, r=40, t=30, b=40))
        st.plotly_chart(fig_evolution, width="stretch", config={"displayModeBar": False})
    else:
        st.info("Não foi possível gerar a evolução mensal porque não há coluna de data reconhecida no conjunto de dados.")
    chart_container_end()
