"""Overview tab rendering functions."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from analytics.processing import SalesAnalytics
from dashboard.components import custom_table, metric_card


def render_overview(sales_df: pd.DataFrame, kpis: dict[str, Any]) -> None:
    """Renders the executive KPI overview tab."""
    st.markdown("### Resumo Executivo")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(
            label="Total de Pedidos",
            value=f"{kpis['total_orders']:,}",
            delta="Pedidos Confirmados",
            delta_type="up",
        )
    with c2:
        metric_card(
            label="Volume Total Vendido (Itens)",
            value=f"{int(kpis['total_qty_sold']):,}",
            delta="Soma de Quantidades",
            delta_type="up",
        )
    with c3:
        metric_card(
            label="Produtos Únicos Comercializados",
            value=f"{kpis['unique_products']:,}",
            delta="Portfólio Ativo",
            delta_type="up",
        )
    with c4:
        metric_card(
            "Clientes Ativos",
            f"{kpis['active_customers']:,}",
            delta="Clientes com Pedidos",
            delta_type="warn" if kpis["active_customers"] < 450 else "up",
        )

    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        metric_card(
            label="Pedidos com Nota Fiscal",
            value=f"{kpis['orders_with_nf']:,}",
            delta="Emitidas com Sucesso",
            delta_type="up",
        )
    with c6:
        metric_card(
            label="Pedidos sem Nota Fiscal",
            value=f"{kpis['orders_without_nf']:,}",
            delta="Aguardando Emissão",
            delta_type="warn" if kpis["orders_without_nf"] > 0 else "up",
        )
    with c7:
        metric_card(
            label="Taxa de Emissão de NF",
            value=f"{kpis['nf_emission_rate']:.2f}%",
            delta="Cobertura Fiscal",
            delta_type="up" if kpis["nf_emission_rate"] > 80 else "warn",
        )
    with c8:
        metric_card(
            label="Pedidos por Cliente",
            value=f"{kpis['orders_per_customer']:.2f}",
            delta="Média Geral",
            delta_type="up",
        )

    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

    st.markdown("#### Destaques de Venda")
    products_pareto_df, _ = SalesAnalytics.get_abc_pareto_analysis(sales_df)
    if not products_pareto_df.empty:
        col_table, col_desc = st.columns([2, 1])
        with col_table:
            custom_table(
                products_pareto_df.head(5)[["Código do Produto", "Quantidade", "Participação (%)", "Classe ABC"]],
                columns_mapping={
                    "Código do Produto": "Código do Produto",
                    "Quantidade": "Quantidade Vendida",
                    "Participação (%)": "Participação",
                    "Classe ABC": "Classe",
                },
            )
        with col_desc:
            st.markdown(
                """
            <div class="insight-card">
                <div class="insight-title">Destaque de Portfólio</div>
                <div class="insight-desc">
                    A tabela ao lado exibe os 5 produtos de maior movimentação física.
                    Monitorar esses itens é crítico para garantir níveis adequados de estoque
                    e evitar gargalos na expedição.
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
