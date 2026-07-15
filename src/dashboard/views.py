import streamlit as st
import plotly.express as px
import plotly.graph_objects as ob
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Any

from dashboard.components import metric_card, custom_table, chart_container, chart_container_end
from analytics.processing import SalesAnalytics

def get_plot_layout(is_dark: bool) -> dict:
    """Returns the base layout configuration for Plotly charts."""
    text_color = "#a1a1aa" if is_dark else "#71717a"
    grid_color = "rgba(255,255,255,0.06)" if is_dark else "rgba(0,0,0,0.06)"
    
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=text_color, size=11),
        margin=dict(l=40, r=40, t=30, b=40),
        xaxis=dict(
            gridcolor=grid_color,
            zerolinecolor=grid_color,
            tickfont=dict(size=10, color=text_color),
        ),
        yaxis=dict(
            gridcolor=grid_color,
            zerolinecolor=grid_color,
            tickfont=dict(size=10, color=text_color),
        ),
    )

def render_overview(df: pd.DataFrame, kpis: Dict[str, Any]) -> None:
    """Renders the executive KPI overview tab."""
    st.markdown("### Resumo Executivo")
    
    # KPI Grid - Row 1
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card(
            label="Total de Pedidos",
            value=f"{kpis['total_orders']:,}",
            delta="Pedidos Confirmados",
            delta_type="up"
        )
    with c2:
        metric_card(
            label="Volume Total Vendido (Itens)",
            value=f"{int(kpis['total_qty_sold']):,}",
            delta="Soma de Quantidades",
            delta_type="up"
        )
    with c3:
        metric_card(
            label="Produtos Únicos Comercializados",
            value=f"{kpis['unique_products']:,}",
            delta="Portfólio Ativo",
            delta_type="up"
        )
        
    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
    
    # KPI Grid - Row 2
    c4, c5, c6 = st.columns(3)
    with c4:
        metric_card(
            label="Pedidos com Nota Fiscal",
            value=f"{kpis['orders_with_nf']:,}",
            delta="Emitidas com Sucesso",
            delta_type="up"
        )
    with c5:
        metric_card(
            label="Pedidos sem Nota Fiscal",
            value=f"{kpis['orders_without_nf']:,}",
            delta="Aguardando Emissão",
            delta_type="warn" if kpis['orders_without_nf'] > 0 else "up"
        )
    with c6:
        metric_card(
            label="Taxa de Emissão de NF",
            value=f"{kpis['nf_emission_rate']:.2f}%",
            delta="Cobertura Fiscal",
            delta_type="up" if kpis['nf_emission_rate'] > 80 else "warn"
        )

    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    # Top Products Small Table
    st.markdown("#### Destaques de Venda")
    df_prod, _ = SalesAnalytics.get_abc_pareto_analysis(df)
    if not df_prod.empty:
        col_table, col_desc = st.columns([2, 1])
        with col_table:
            custom_table(
                df_prod.head(5)[["Código do Produto", "Quantidade", "Participação (%)", "Classe ABC"]],
                columns_mapping={
                    "Código do Produto": "Código do Produto",
                    "Quantidade": "Quantidade Vendida",
                    "Participação (%)": "Participação",
                    "Classe ABC": "Classe"
                }
            )
        with col_desc:
            st.markdown("""
            <div class="insight-card">
                <div class="insight-title">Destaque de Portfólio</div>
                <div class="insight-desc">
                    A tabela ao lado exibe os 5 produtos de maior movimentação física. 
                    Monitorar esses itens é crítico para garantir níveis adequados de estoque 
                    e evitar gargalos na expedição.
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_products(df: pd.DataFrame, is_dark: bool) -> None:
    """Renders the product analytics tab including Top Products, Pareto and ABC Curve."""
    st.markdown("### Análise de Produtos")
    
    # 1. Top Products Selection
    chart_container("Ranking de Produtos Mais Vendidos", "Selecione o limite de exibição")
    limit = st.radio("Quantidade de itens no ranking:", [10, 20], horizontal=True)
    
    df_prod, class_counts = SalesAnalytics.get_abc_pareto_analysis(df)
    
    if not df_prod.empty:
        df_top = df_prod.head(limit).copy()
        # Sort ascending for horizontal bar chart rendering
        df_top = df_top.sort_values(by="Quantidade", ascending=True)
        
        fig_top = px.bar(
            df_top,
            x="Quantidade",
            y="Código do Produto",
            orientation="h",
            labels={"Quantidade": "Volume Vendido", "Código do Produto": "Produto"},
            color_discrete_sequence=["#2563eb"]
        )
        fig_top.update_layout(get_plot_layout(is_dark))
        fig_top.update_layout(margin=dict(l=100, r=40, t=10, b=40))
        st.plotly_chart(fig_top, use_container_width=True, config={"displayModeBar": False})
    chart_container_end()
    
    # 2. Pareto Chart
    if not df_prod.empty:
        chart_container("Gráfico de Pareto (Regra 80/20)", "Participação individual de vendas vs volume acumulado")
        
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Bars for individual quantity
        fig_pareto.add_trace(
            ob.Bar(
                x=df_prod["Código do Produto"],
                y=df_prod["Quantidade"],
                name="Qtd Vendida",
                marker_color="#2563eb",
                opacity=0.85
            ),
            secondary_y=False
        )
        
        # Line for cumulative percentage
        fig_pareto.add_trace(
            ob.Scatter(
                x=df_prod["Código do Produto"],
                y=df_prod["Acumulado (%)"],
                name="% Acumulado",
                line=dict(color="#d97706", width=3),
                mode="lines+markers"
            ),
            secondary_y=True
        )
        
        fig_pareto.update_layout(get_plot_layout(is_dark))
        fig_pareto.update_yaxes(title_text="Quantidade (Itens)", secondary_y=False)
        fig_pareto.update_yaxes(title_text="Percentual Acumulado (%)", range=[0, 105], secondary_y=True)
        fig_pareto.update_xaxes(title_text="Produtos")
        
        st.plotly_chart(fig_pareto, use_container_width=True, config={"displayModeBar": False})
        chart_container_end()
        
    # 3. ABC Curve Classification
    st.markdown("#### Curva ABC (Classificação de Estoque)")
    
    col_abc_chart, col_abc_table = st.columns([1, 1])
    
    with col_abc_chart:
        chart_container("Distribuição por Classe ABC", "Participação de itens em cada faixa de faturamento físico")
        
        abc_data = pd.DataFrame({
            "Classe": list(class_counts.keys()),
            "Qtd Produtos": list(class_counts.values())
        })
        
        # Compute percentages
        total_items = abc_data["Qtd Produtos"].sum()
        abc_data["Participação (%)"] = (abc_data["Qtd Produtos"] / total_items * 100) if total_items > 0 else 0.0
        
        fig_abc = px.bar(
            abc_data,
            x="Classe",
            y="Qtd Produtos",
            text="Qtd Produtos",
            color="Classe",
            color_discrete_map={"A": "#2563eb", "B": "#f59e0b", "C": "#16a34a"},
            labels={"Qtd Produtos": "Quantidade de SKU", "Classe": "Classe ABC"}
        )
        fig_abc.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_abc, use_container_width=True, config={"displayModeBar": False})
        chart_container_end()
        
    with col_abc_table:
        st.markdown("##### Produtos Classificados")
        custom_table(
            df_prod[["Código do Produto", "Quantidade", "Classe ABC"]],
            columns_mapping={
                "Código do Produto": "Código do Produto",
                "Quantidade": "Qtd Total Vendida",
                "Classe ABC": "Classe"
            }
        )


def render_orders(df: pd.DataFrame, is_dark: bool) -> None:
    """Renders the order distribution tab."""
    st.markdown("### Análise de Pedidos")
    
    stats, largest_orders = SalesAnalytics.get_order_stats(df)
    
    # Render Stats Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Média de Itens/Pedido", f"{stats['mean']:.1f}", delta="Volume Médio")
    with c2:
        metric_card("Mediana de Itens/Pedido", f"{stats['median']:.1f}", delta="Mediana Real")
    with c3:
        metric_card("Volume Máximo em Pedido", f"{int(stats['max']):,}", delta="Maior Pedido", delta_type="up")
    with c4:
        metric_card("Volume Mínimo em Pedido", f"{int(stats['min']):,}", delta="Menor Pedido")
        
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    # Charts Row
    col_hist, col_box = st.columns(2)
    
    with col_hist:
        chart_container("Distribuição de Volumes dos Pedidos", "Frequência de pedidos por faixa de quantidade de itens")
        if not largest_orders.empty:
            fig_hist = px.histogram(
                largest_orders,
                x="Quantidade",
                nbins=20,
                labels={"Quantidade": "Quantidade de Itens por Pedido", "count": "Frequência"},
                color_discrete_sequence=["#2563eb"]
            )
            fig_hist.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})
        chart_container_end()
        
    with col_box:
        chart_container("Dispersão e Outliers de Volumes", "Visualização de quartis e valores discrepantes (box plot)")
        if not largest_orders.empty:
            fig_box = px.box(
                largest_orders,
                y="Quantidade",
                labels={"Quantidade": "Itens por Pedido"},
                color_discrete_sequence=["#d97706"]
            )
            fig_box.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_box, use_container_width=True, config={"displayModeBar": False})
        chart_container_end()
        
    # Largest Orders List
    st.markdown("#### Ranking de Pedidos de Maior Volume")
    if not largest_orders.empty:
        col_tab, col_info = st.columns([2, 1])
        with col_tab:
            custom_table(
                largest_orders.head(10),
                columns_mapping={
                    "Pedido ID": "Pedido ID",
                    "Número do Pedido": "Número do Pedido",
                    "Quantidade": "Volume Total (Itens)"
                }
            )
        with col_info:
            st.markdown("""
            <div class="insight-card">
                <div class="insight-title">Análise de Concentração</div>
                <div class="insight-desc">
                    Identificar os maiores pedidos ajuda a monitorar os clientes mais valiosos 
                    e prever a necessidade de logística especial ou negociações comerciais dedicadas.
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_geography(df: pd.DataFrame, is_dark: bool) -> None:
    """Renders geographic revenue and customer distribution analytics."""
    st.markdown("### Geografia de Vendas")
    
    state_clients = SalesAnalytics.get_clients_by_state(df)
    state_revenue = SalesAnalytics.get_state_revenue(df)
    state_ticket = SalesAnalytics.get_state_ticket_average(df)
    top_cities_revenue = SalesAnalytics.get_top_cities_by_revenue(df)
    top_cities_customers = SalesAnalytics.get_top_cities_by_customers(df)
    state_geo = SalesAnalytics.get_state_geo_coordinates(df)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Estados com Clientes", f"{len(state_clients):,}", delta="Cobertura Regional")
    with c2:
        metric_card("Estados com Receita", f"{len(state_revenue):,}", delta="Estados Ativos")
    with c3:
        metric_card("Cidades com Receita", f"{len(top_cities_revenue):,}", delta="Top 10 visível")

    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)

    chart_container("Receita por Estado", "Valor total faturado por UF")
    if not state_revenue.empty:
        fig_state_rev = px.bar(
            state_revenue,
            x="UF",
            y="Valor_Total",
            labels={"UF": "Estado", "Valor_Total": "Receita Total"},
            color="Valor_Total",
            color_continuous_scale="Blues",
            text_auto=",.0f"
        )
        fig_state_rev.update_layout(get_plot_layout(is_dark))
        fig_state_rev.update_yaxes(tickformat=",.0f")
        st.plotly_chart(fig_state_rev, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Não há dados de faturamento por estado disponíveis.")
    chart_container_end()

    chart_container("Clientes por Estado (UF)", "Quantidade de clientes compradores por estado")
    if not state_clients.empty:
        df_clients_pct = state_clients.copy()
        total_clients = df_clients_pct["Clientes"].sum()
        df_clients_pct["Participação Clientes (%)"] = df_clients_pct["Clientes"] / total_clients * 100 if total_clients > 0 else 0.0
        fig_clients = px.bar(
            df_clients_pct.sort_values("Clientes", ascending=False),
            x="UF",
            y="Clientes",
            labels={"UF": "Estado", "Clientes": "Clientes Compradores"},
            text_auto=True,
            color="Clientes",
            color_continuous_scale="Viridis"
        )
        fig_clients.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_clients, use_container_width=True, config={"displayModeBar": False})
        custom_table(
            df_clients_pct[["UF", "Clientes", "Participação Clientes (%)"]].sort_values("Clientes", ascending=False),
            columns_mapping={"UF": "UF", "Clientes": "Clientes Compradores", "Participação Clientes (%)": "% Participação"}
        )
    else:
        st.info("Não há dados de clientes por estado disponíveis.")
    chart_container_end()

    chart_container("Ticket Médio por Estado", "Faturamento total dividido pela quantidade de clientes compradores")
    if not state_ticket.empty:
        fig_ticket = px.bar(
            state_ticket,
            x="UF",
            y="Ticket Médio",
            labels={"UF": "Estado", "Ticket Médio": "Ticket Médio (R$)"},
            text_auto=",.0f",
            color="Ticket Médio",
            color_continuous_scale="Cividis"
        )
        fig_ticket.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_ticket, use_container_width=True, config={"displayModeBar": False})
        custom_table(
            state_ticket[["UF", "Clientes", "Valor_Total", "Ticket Médio", "Participação Clientes (%)", "Participação Receita (%)"]].rename(
                columns={
                    "Valor_Total": "Receita Total"
                }
            ),
            columns_mapping={
                "UF": "UF",
                "Clientes": "Clientes Compradores",
                "Receita Total": "Receita Total",
                "Ticket Médio": "Ticket Médio",
                "Participação Clientes (%)": "% Clientes",
                "Participação Receita (%)": "% Receita"
            }
        )
    else:
        st.info("Não há dados de ticket médio por estado disponíveis.")
    chart_container_end()

    chart_container("Top 10 Cidades por Faturamento", "As cidades que mais contribuem para a receita")
    if not top_cities_revenue.empty:
        fig_top_city_rev = px.bar(
            top_cities_revenue.sort_values("Valor_Total", ascending=True),
            x="Valor_Total",
            y="Cidade",
            orientation="h",
            labels={"Valor_Total": "Receita Total", "Cidade": "Cidade"},
            color="Valor_Total",
            color_continuous_scale="Oranges",
            text_auto=",.0f"
        )
        fig_top_city_rev.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_top_city_rev, use_container_width=True, config={"displayModeBar": False})
    chart_container_end()

    chart_container("Top 10 Cidades por Clientes", "As cidades com maior base de compradores")
    if not top_cities_customers.empty:
        fig_top_city_cust = px.bar(
            top_cities_customers.sort_values("Clientes", ascending=True),
            x="Clientes",
            y="Cidade",
            orientation="h",
            labels={"Clientes": "Clientes Compradores", "Cidade": "Cidade"},
            color="Clientes",
            color_continuous_scale="Blues",
            text_auto=True
        )
        fig_top_city_cust.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_top_city_cust, use_container_width=True, config={"displayModeBar": False})
    chart_container_end()

    chart_container("Mapa de Calor Geográfico por Estado", "Visualização de concentração regional de receita")
    if not state_geo.empty:
        fig_map = px.scatter_geo(
            state_geo,
            lat="Latitude",
            lon="Longitude",
            color="Valor_Total",
            size="Valor_Total",
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
        fig_map.update_geos(fitbounds="locations", visible=False)
        fig_map.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("O mapa geográfico não pôde ser gerado porque não há coordenadas válidas para os estados.")
    chart_container_end()

    chart_container("Participação de Cada Estado na Receita Total", "Percentual do faturamento por UF")
    if not state_ticket.empty:
        fig_state_share = px.pie(
            state_ticket,
            values="Participação Receita (%)",
            names="UF",
            hole=0.45,
            color_discrete_sequence=px.colors.sequential.Plasma
        )
        fig_state_share.update_layout(get_plot_layout(is_dark))
        st.plotly_chart(fig_state_share, use_container_width=True, config={"displayModeBar": False})
    chart_container_end()

    st.markdown("<div style='margin: 1.25rem 0;'></div>", unsafe_allow_html=True)
    st.markdown("#### Observações Importantes")
    st.markdown("""
    - Os valores de UF são inferidos primeiro a partir dos dados da nota fiscal, com fallback para o CEP quando necessário.
    - O mapa geográfico é construído internamente usando centroides de estados brasileiros, sem qualquer serviço externo.
    - Quando a cidade não está disponível na nota fiscal, o estado ainda é utilizado para análise regional.
    """, unsafe_allow_html=True)


def render_fiscal(df: pd.DataFrame, is_dark: bool) -> None:
    """Renders the fiscal status and invoice compliance tab."""
    st.markdown("### Painel de Conformidade Fiscal")
    
    kpis = SalesAnalytics.calculate_kpis(df)
    
    # Cards
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Pedidos com Nota Fiscal", f"{kpis['orders_with_nf']}", delta="Faturamento Fiscal")
    with c2:
        metric_card("Pedidos sem Nota Fiscal", f"{kpis['orders_without_nf']}", delta="Pendente", delta_type="warn" if kpis['orders_without_nf'] > 0 else "up")
    with c3:
        metric_card("Taxa de Emissão de NF", f"{kpis['nf_emission_rate']:.1f}%", delta="Compliance", delta_type="up" if kpis['nf_emission_rate'] > 80 else "warn")
        
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    # Gauge and Donut Chart
    col_gauge, col_donut = st.columns(2)
    
    with col_gauge:
        chart_container("Taxa de Cobertura Fiscal (Emissão)", "Percentual de pedidos com nota fiscal transmitida")
        
        # Gauge chart using plotly graph_objects
        fig_gauge = ob.Figure(ob.Indicator(
            mode = "gauge+number",
            value = kpis['nf_emission_rate'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            number = {'suffix': "%", 'font': {'size': 40}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "gray"},
                'bar': {'color': "#2563eb"},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 2,
                'bordercolor': "#1e1e24" if is_dark else "#e4e4e7",
                'steps': [
                    {'range': [0, 50], 'color': 'rgba(239,68,68,0.1)'},
                    {'range': [50, 85], 'color': 'rgba(245,158,11,0.1)'},
                    {'range': [85, 100], 'color': 'rgba(34,197,94,0.1)'}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        
        # Apply standard layout styling
        fig_gauge.update_layout(get_plot_layout(is_dark))
        fig_gauge.update_layout(height=260, margin=dict(l=30, r=30, t=40, b=10))
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
        chart_container_end()
        
    with col_donut:
        chart_container("Distribuição por Status das NF", "Quantidade de pedidos por status de faturamento")
        df_fiscal = SalesAnalytics.get_fiscal_distribution(df)
        
        if not df_fiscal.empty:
            fig_donut = px.pie(
                df_fiscal,
                values="Quantidade",
                names="Status da Nota Fiscal",
                hole=0.5,
                color="Status da Nota Fiscal",
                color_discrete_map={"ACEITA": "#16a34a", "Não emitida": "#ef4444", "DENEGADA": "#f59e0b", "REJEITADA": "#dc2626"}
            )
            fig_donut.update_layout(get_plot_layout(is_dark))
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
        chart_container_end()


def render_insights(df: pd.DataFrame, kpis: Dict[str, Any]) -> None:
    """Renders the executive insights and manager recommendations page."""
    st.markdown("### Relatório de Insights Gerenciais")
    
    # 1. Fetch products analysis for insights
    df_prod, class_counts = SalesAnalytics.get_abc_pareto_analysis(df)
    
    if df_prod.empty:
        st.info("Nenhum dado disponível para gerar insights.")
        return
        
    # Calculations for insights
    top1_name = df_prod.iloc[0]["Código do Produto"]
    top1_qty = int(df_prod.iloc[0]["Quantidade"])
    
    # Concentration calculation
    top5_qty = df_prod.head(5)["Quantidade"].sum()
    top10_qty = df_prod.head(10)["Quantidade"].sum()
    total_qty = df_prod["Quantidade"].sum()
    
    pct_top5 = (top5_qty / total_qty * 100) if total_qty > 0 else 0.0
    pct_top10 = (top10_qty / total_qty * 100) if total_qty > 0 else 0.0
    
    # Number of class A items
    count_class_a = class_counts.get("A", 0)
    
    # Render Insights List
    st.markdown("#### Destaques Operacionais")
    
    # Insight 1: Most sold product
    st.markdown(f"""
    <div class="insight-card">
        <div class="insight-title">🥇 Produto Mais Vendido</div>
        <div class="insight-desc">
            O produto <strong>{top1_name}</strong> é o líder absoluto de vendas com <strong>{top1_qty:,} unidades</strong> comercializadas, 
            representando <strong>{(top1_qty / total_qty * 100):.2f}%</strong> do volume total. Recomenda-se atenção prioritária 
            ao estoque de segurança deste SKU.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Insight 2: Concentration
    st.markdown(f"""
    <div class="insight-card">
        <div class="insight-title">📈 Concentração de Vendas (Pareto)</div>
        <div class="insight-desc">
            Os 5 produtos mais vendidos respondem por <strong>{pct_top5:.2f}%</strong> das vendas, enquanto os Top 10 representam 
            <strong>{pct_top10:.2f}%</strong> do volume total comercializado. Isso indica uma 
            <strong>{'alta' if pct_top10 > 60 else 'moderada'} concentração de vendas</strong> no portfólio, tornando a operação 
            dependente do desempenho de poucos produtos.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Insight 3: ABC Inventory
    st.markdown(f"""
    <div class="insight-card">
        <div class="insight-title">📦 Gestão de Categorias ABC</div>
        <div class="insight-desc">
            Apenas <strong>{count_class_a} produtos</strong> foram classificados na <strong>Classe A</strong> da curva ABC. 
            Esses SKUs constituem a espinha dorsal de sua cadeia de suprimentos física e devem passar por inventários rotativos frequentes 
            para evitar rupturas de estoque.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Insight 4: Fiscal Compliance
    pending_pct = 100.0 - kpis['nf_emission_rate']
    st.markdown(f"""
    <div class="insight-card">
        <div class="insight-title">⚖️ Compliance Fiscal</div>
        <div class="insight-desc">
            Atualmente, <strong>{kpis['nf_emission_rate']:.2f}%</strong> dos pedidos possuem notas fiscais emitidas. 
            Há um montante de <strong>{kpis['orders_without_nf']} pedido(s) (ou {pending_pct:.2f}% do total)</strong> pendentes de emissão fiscal. 
            Acelerar esse processo é fundamental para garantir a legalidade do transporte de mercadorias e a saúde de faturamento.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Executive Recommendations Summary
    st.markdown("#### Recomendações Estratégicas para a Diretoria")
    st.markdown(f"""
    1. **Otimização de Supply Chain**: Garantir contrato de fornecimento estável ou produção programada para o produto lider **{top1_name}** e demais itens da **Classe A**.
    2. **Mitigação de Risco de Portfólio**: Desenvolver estratégias promocionais para diversificar as vendas e reduzir a alta concentração física observada nos Top 5 produtos ({pct_top5:.1f}%).
    3. **Automatização Fiscal**: Implementar gatilhos de faturamento integrado para diminuir a fila de {kpis['orders_without_nf']} pedido(s) pendente(s) de emissão fiscal.
    """)
