"""Insights tab rendering functions."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from analytics.processing import SalesAnalytics


def render_insights(sales_df: pd.DataFrame, kpis: dict[str, Any]) -> None:
    """Renders the executive insights and manager recommendations page."""
    st.markdown("### Relatório de Insights Gerenciais")

    products_abc_df, class_counts = SalesAnalytics.get_abc_pareto_analysis(sales_df)
    if products_abc_df.empty:
        st.info("Nenhum dado disponível para gerar insights.")
        return

    top1_name = products_abc_df.iloc[0]["Código do Produto"]
    top1_qty = int(products_abc_df.iloc[0]["Quantidade"])

    top5_qty = products_abc_df.head(5)["Quantidade"].sum()
    top10_qty = products_abc_df.head(10)["Quantidade"].sum()
    total_qty = products_abc_df["Quantidade"].sum()

    pct_top5 = (top5_qty / total_qty * 100) if total_qty > 0 else 0.0
    pct_top10 = (top10_qty / total_qty * 100) if total_qty > 0 else 0.0
    count_class_a = class_counts.get("A", 0)

    st.markdown("#### Destaques Operacionais")

    st.markdown(
        f"""
    <div class="insight-card">
        <div class="insight-title">🥇 Produto Mais Vendido</div>
        <div class="insight-desc">
            O produto <strong>{top1_name}</strong> é o líder absoluto de vendas com <strong>{top1_qty:,} unidades</strong> comercializadas,
            representando <strong>{(top1_qty / total_qty * 100):.2f}%</strong> do volume total. Recomenda-se atenção prioritária
            ao estoque de segurança deste SKU.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <div class="insight-card">
        <div class="insight-title">📈 Concentração de Vendas (Pareto)</div>
        <div class="insight-desc">
            Os 5 produtos mais vendidos respondem por <strong>{pct_top5:.2f}%</strong> das vendas, enquanto os Top 10 representam
            <strong>{pct_top10:.2f}%</strong> do volume total comercializado. Isso indica uma
            <strong>{'alta' if pct_top10 > 60 else 'moderada'} concentração de vendas</strong> no portfólio, tornando a operação
            dependente do desempenho de poucos produtos.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <div class="insight-card">
        <div class="insight-title">📦 Gestão de Categorias ABC</div>
        <div class="insight-desc">
            Apenas <strong>{count_class_a} produtos</strong> foram classificados na <strong>Classe A</strong> da curva ABC.
            Esses SKUs constituem a espinha dorsal de sua cadeia de suprimentos física e devem passar por inventários rotativos frequentes
            para evitar rupturas de estoque.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    pending_pct = 100.0 - kpis["nf_emission_rate"]
    st.markdown(
        f"""
    <div class="insight-card">
        <div class="insight-title">⚖️ Compliance Fiscal</div>
        <div class="insight-desc">
            Atualmente, <strong>{kpis['nf_emission_rate']:.2f}%</strong> dos pedidos possuem notas fiscais emitidas.
            Há um montante de <strong>{kpis['orders_without_nf']} pedido(s) (ou {pending_pct:.2f}% do total)</strong> pendentes de emissão fiscal.
            Acelerar esse processo é fundamental para garantir a legalidade do transporte de mercadorias e a saúde de faturamento.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Recomendações Estratégicas para a Diretoria")
    st.markdown(
        f"""
    1. **Otimização de Supply Chain**: Garantir contrato de fornecimento estável ou produção programada para o produto lider **{top1_name}** e demais itens da **Classe A**.
    2. **Mitigação de Risco de Portfólio**: Desenvolver estratégias promocionais para diversificar as vendas e reduzir a alta concentração física observada nos Top 5 produtos ({pct_top5:.1f}%).
    3. **Automatização Fiscal**: Implementar gatilhos de faturamento integrado para diminuir a fila de {kpis['orders_without_nf']} pedido(s) pendente(s) de emissão fiscal.
    """
    )
