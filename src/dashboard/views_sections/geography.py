"""Geography tab rendering functions."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.processing import SalesAnalytics
from dashboard.components import chart_container, chart_container_end, custom_table, metric_card
from dashboard.views_sections.common import get_plot_layout


def render_geography(sales_df: pd.DataFrame, is_dark: bool) -> None:
    """Renders geographic revenue and customer distribution analytics."""
    st.markdown("### Geografia de Vendas")

    state_clients_df = SalesAnalytics.get_clients_by_state(sales_df)
    state_revenue_df = SalesAnalytics.get_state_revenue(sales_df)
    state_ticket_df = SalesAnalytics.get_state_ticket_average(sales_df)
    top_cities_revenue_df = SalesAnalytics.get_top_cities_by_revenue(sales_df)
    top_cities_customers_df = SalesAnalytics.get_top_cities_by_customers(sales_df)
    state_geo_df = SalesAnalytics.get_state_geo_coordinates(sales_df)

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Estados com Clientes", f"{len(state_clients_df):,}", delta="Cobertura Regional")
    with c2:
        metric_card("Estados com Receita", f"{len(state_revenue_df):,}", delta="Estados Ativos")
    with c3:
        metric_card("Cidades com Receita", f"{len(top_cities_revenue_df):,}", delta="Top 10 visível")

    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

    chart_container("Receita por Estado", "Valor total faturado por UF")
    if not state_revenue_df.empty:
        fig_state_revenue = px.bar(
            state_revenue_df,
            x="UF",
            y="Valor_Total",
            labels={"UF": "Estado", "Valor_Total": "Receita Total"},
            color="Valor_Total",
            color_continuous_scale="Blues",
            text_auto=",.0f",
        )
        fig_state_revenue.update_layout(get_plot_layout(is_dark))
        fig_state_revenue.update_yaxes(tickformat=",.0f")
        st.plotly_chart(fig_state_revenue, width="stretch", config={"displayModeBar": False})
    else:
        st.info("Não há dados de faturamento por estado disponíveis.")
    chart_container_end()

    chart_container("Clientes por Estado (UF)", "Quantidade de clientes compradores por estado")
    if not state_clients_df.empty:
        clients_distribution_df = state_clients_df.copy()
        total_clients = clients_distribution_df["Clientes"].sum()
        clients_distribution_df["Participação Clientes (%)"] = (
            clients_distribution_df["Clientes"] / total_clients * 100
            if total_clients > 0
            else 0.0
        )
        fig_clients = px.bar(
            clients_distribution_df.sort_values("Clientes", ascending=False),
            x="UF",
            y="Clientes",
            labels={"UF": "Estado", "Clientes": "Clientes Compradores"},
            text_auto=True,
            color="Clientes",
            color_continuous_scale="Viridis",
        )
        fig_clients.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_clients, width="stretch", config={"displayModeBar": False})
        custom_table(
            clients_distribution_df[["UF", "Clientes", "Participação Clientes (%)"]].sort_values("Clientes", ascending=False),
            columns_mapping={"UF": "UF", "Clientes": "Clientes Compradores", "Participação Clientes (%)": "% Participação"},
        )
    else:
        st.info("Não há dados de clientes por estado disponíveis.")
    chart_container_end()

    chart_container("Ticket Médio por Estado", "Faturamento total dividido pela quantidade de clientes compradores")
    st.caption("Estados com poucos pedidos foram excluídos desta análise para evitar distorções estatísticas.")
    if not state_ticket_df.empty:
        fig_ticket = px.bar(
            state_ticket_df,
            x="UF",
            y="Ticket Médio",
            labels={"UF": "Estado", "Ticket Médio": "Ticket Médio (R$)"},
            text_auto=",.0f",
            color="Ticket Médio",
            color_continuous_scale="Cividis",
        )
        fig_ticket.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_ticket, width="stretch", config={"displayModeBar": False})
        custom_table(
            state_ticket_df[["UF", "Pedidos", "Clientes", "Valor_Total", "Ticket Médio", "Participação Clientes (%)", "Participação Receita (%)"]].rename(
                columns={"Valor_Total": "Receita Total"}
            ),
            columns_mapping={
                "UF": "UF",
                "Pedidos": "Pedidos",
                "Clientes": "Clientes Compradores",
                "Receita Total": "Receita Total",
                "Ticket Médio": "Ticket Médio",
                "Participação Clientes (%)": "% Clientes",
                "Participação Receita (%)": "% Receita",
            },
        )
    else:
        st.info("Não há dados de ticket médio por estado disponíveis.")
    chart_container_end()

    chart_container("Top 10 Cidades por Faturamento", "As cidades que mais contribuem para a receita")
    if not top_cities_revenue_df.empty:
        fig_top_city_revenue = px.bar(
            top_cities_revenue_df.sort_values("Valor_Total", ascending=True),
            x="Valor_Total",
            y="Cidade",
            orientation="h",
            labels={"Valor_Total": "Receita Total", "Cidade": "Cidade"},
            color="Valor_Total",
            color_continuous_scale="Oranges",
            text_auto=",.0f",
        )
        fig_top_city_revenue.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_top_city_revenue, width="stretch", config={"displayModeBar": False})
    chart_container_end()

    chart_container("Top 10 Cidades por Clientes", "As cidades com maior base de compradores")
    if not top_cities_customers_df.empty:
        fig_top_city_customers = px.bar(
            top_cities_customers_df.sort_values("Clientes", ascending=True),
            x="Clientes",
            y="Cidade",
            orientation="h",
            labels={"Clientes": "Clientes Compradores", "Cidade": "Cidade"},
            color="Clientes",
            color_continuous_scale="Blues",
            text_auto=True,
        )
        fig_top_city_customers.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_top_city_customers, width="stretch", config={"displayModeBar": False})
    chart_container_end()

    chart_container("Mapa de Calor Geográfico por Estado", "Visualização de concentração regional de receita")
    if not state_geo_df.empty:
        fig_map = px.scatter_geo(
            state_geo_df,
            lat="Latitude",
            lon="Longitude",
            color="Valor_Total",
            size="Valor_Total",
            size_max=40,
            hover_name="UF",
            hover_data={
                "Clientes": True,
                "Ticket Médio": ":.2f",
                "Valor_Total": ":,.0f",
                "Latitude": False,
                "Longitude": False,
            },
            projection="natural earth",
            color_continuous_scale="reds",
            title="",
        )
        fig_map.update_traces(marker=dict(opacity=0.85, line=dict(width=1, color="#2a2a2a")))
        fig_map.update_geos(
            fitbounds="locations",
            visible=True,
            showland=True,
            landcolor="#f2f2f2",
            showocean=True,
            oceancolor="#ddeeff",
            showcountries=True,
            countrycolor="#7f7f7f",
            coastlinecolor="#7f7f7f",
            lataxis=dict(range=[-35, 10]),
            lonaxis=dict(range=[-75, -30]),
        )
        fig_map.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_map, width="stretch", config={"displayModeBar": False})
    else:
        st.info("O mapa geográfico não pôde ser gerado porque não há coordenadas válidas para os estados.")
    chart_container_end()

    chart_container("Participação de Cada Estado na Receita Total", "Percentual do faturamento por UF")
    if not state_ticket_df.empty:
        fig_state_share = px.pie(
            state_ticket_df,
            values="Participação Receita (%)",
            names="UF",
            hole=0.45,
            color_discrete_sequence=px.colors.sequential.Plasma,
        )
        fig_state_share.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_state_share, width="stretch", config={"displayModeBar": False})
    chart_container_end()

    st.markdown("<div style='margin: 1.25rem 0;'></div>", unsafe_allow_html=True)
    st.markdown("#### Observações Importantes")
    st.markdown(
        """
    - Os valores de UF são inferidos primeiro a partir dos dados da nota fiscal, com fallback para o CEP quando necessário.
    - O mapa geográfico é construído internamente usando centroides de estados brasileiros, sem qualquer serviço externo.
    - Quando a cidade não está disponível na nota fiscal, o estado ainda é utilizado para análise regional.
    """,
        unsafe_allow_html=True,
    )
