"""Product and order tab rendering functions."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import plotly.express as px
import plotly.graph_objects as ob
import streamlit as st
from plotly.subplots import make_subplots

from analytics.processing import SalesAnalytics
from dashboard.components import chart_container, chart_container_end, custom_table, metric_card
from dashboard.views_sections.common import get_plot_layout


PRODUCT_COLOR_SEQUENCE = [
    "#2563eb",
    "#d97706",
    "#16a34a",
    "#7c3aed",
    "#dc2626",
]


VALID_PRODUCT_CODE_PATTERN = r"^ALL\d{4}$"


def _filter_valid_all_products(sales_df: pd.DataFrame) -> pd.DataFrame:
    """Keeps only rows with product codes in the ALL + 4 numeric digits format."""
    if sales_df.empty or "Código do Produto" not in sales_df.columns:
        return pd.DataFrame(columns=sales_df.columns)

    filtered_df = sales_df.copy()
    normalized_codes = filtered_df["Código do Produto"].astype(str).str.strip().str.upper()
    valid_mask = normalized_codes.str.match(VALID_PRODUCT_CODE_PATTERN, na=False)
    filtered_df = filtered_df.loc[valid_mask].copy()
    filtered_df["Código do Produto"] = normalized_codes.loc[filtered_df.index]
    return filtered_df


def _resolve_date_column(df: pd.DataFrame) -> str | None:
    """Finds the first parsable date column in the dataset."""
    if df.empty:
        return None

    preferred_candidates = ["Data do Pedido", "Data da Venda", "Data", "date"]
    for column in preferred_candidates:
        if column in df.columns:
            parsed = pd.to_datetime(df[column], errors="coerce")
            if parsed.notna().any():
                return column

    for column in df.columns:
        if "data" not in column.lower() and "date" not in column.lower():
            continue
        parsed = pd.to_datetime(df[column], errors="coerce")
        if parsed.notna().any():
            return column

    return None


def _build_product_label_map(analytics: SalesAnalytics | None) -> dict[str, str]:
    """Builds readable product labels from the catalog when available."""
    if analytics is None or getattr(analytics, "products_df", None) is None or analytics.products_df.empty:
        return {}

    catalog_df = analytics.products_df.copy()
    if "Código" not in catalog_df.columns:
        return {}

    catalog_df["Código"] = catalog_df["Código"].astype(str).str.strip().str.upper()
    if "Descrição" not in catalog_df.columns:
        return {code: code for code in catalog_df["Código"].dropna().tolist()}

    catalog_df["Descrição"] = catalog_df["Descrição"].astype(str).str.strip()

    label_map: dict[str, str] = {}
    for _, row in catalog_df.iterrows():
        code = str(row.get("Código") or "").strip().upper()
        description = str(row.get("Descrição") or "").strip()
        if not code:
            continue
        if not description or description.lower() in {"nan", "none", "n/a"}:
            label_map[code] = code
        else:
            label_map[code] = f"{description} ({code})"

    return label_map


def _build_top_products_timeline(
    sales_df: pd.DataFrame,
    analytics: SalesAnalytics | None,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict[str, str]]:
    """Builds the monthly grouped volume and participation datasets for the top 5 products."""
    if sales_df.empty or "Código do Produto" not in sales_df.columns:
        return pd.DataFrame(), pd.DataFrame(), [], {}

    date_column = _resolve_date_column(sales_df)
    if date_column is None:
        return pd.DataFrame(), pd.DataFrame(), [], {}

    working_df = sales_df.copy()
    working_df[date_column] = pd.to_datetime(working_df[date_column], errors="coerce")
    working_df = working_df[working_df[date_column].notna()].copy()
    if working_df.empty:
        return pd.DataFrame(), pd.DataFrame(), [], {}

    working_df["_month"] = working_df[date_column].dt.to_period("M").dt.to_timestamp()
    working_df["Código do Produto"] = working_df["Código do Produto"].astype(str).str.strip().str.upper()
    working_df["Quantidade"] = pd.to_numeric(working_df.get("Quantidade", 0.0), errors="coerce").fillna(0.0)

    top_products_df = (
        working_df.groupby("Código do Produto", as_index=False)["Quantidade"]
        .sum()
        .sort_values("Quantidade", ascending=False)
        .head(5)
    )

    top_product_codes = top_products_df["Código do Produto"].tolist()
    if not top_product_codes:
        return pd.DataFrame(), pd.DataFrame(), [], {}

    label_map = _build_product_label_map(analytics)
    product_labels = {
        code: label_map.get(code, code)
        for code in top_product_codes
    }

    monthly_totals_df = (
        working_df.groupby("_month", as_index=False)["Quantidade"]
        .sum()
        .rename(columns={"Quantidade": "Total do Mês"})
    )

    monthly_top_df = (
        working_df[working_df["Código do Produto"].isin(top_product_codes)]
        .groupby(["_month", "Código do Produto"], as_index=False)["Quantidade"]
        .sum()
        .merge(monthly_totals_df, on="_month", how="left")
    )

    if monthly_top_df.empty:
        return pd.DataFrame(), pd.DataFrame(), top_product_codes, product_labels

    monthly_top_df["Participação (%)"] = (
        monthly_top_df["Quantidade"] / monthly_top_df["Total do Mês"] * 100
    ).fillna(0.0)
    monthly_top_df["Produto"] = monthly_top_df["Código do Produto"].map(product_labels)
    monthly_top_df["Mês"] = monthly_top_df["_month"]

    top_order = [product_labels[code] for code in top_product_codes]
    monthly_top_df["Produto"] = pd.Categorical(monthly_top_df["Produto"], categories=top_order, ordered=True)
    monthly_top_df = monthly_top_df.sort_values(["_month", "Produto"]).reset_index(drop=True)

    return monthly_top_df, monthly_totals_df, top_product_codes, product_labels


def _build_color_map(product_order: Sequence[str]) -> dict[str, str]:
    """Assigns consistent colors to the selected products."""
    return {
        product: PRODUCT_COLOR_SEQUENCE[index % len(PRODUCT_COLOR_SEQUENCE)]
        for index, product in enumerate(product_order)
    }


def _build_last_sale_list(
    sales_df: pd.DataFrame,
    analytics: SalesAnalytics | None,
) -> pd.DataFrame:
    """Builds product last-sale list and inactivity flag (>3 months without sales)."""
    if sales_df.empty or "Código do Produto" not in sales_df.columns:
        return pd.DataFrame()

    date_column = _resolve_date_column(sales_df)
    if date_column is None:
        return pd.DataFrame()

    working_df = sales_df.copy()
    working_df[date_column] = pd.to_datetime(working_df[date_column], errors="coerce")
    working_df = working_df[working_df[date_column].notna()].copy()
    if working_df.empty:
        return pd.DataFrame()

    working_df["Código do Produto"] = working_df["Código do Produto"].astype(str).str.strip().str.upper()

    last_sale_df = (
        working_df.groupby("Código do Produto", as_index=False)[date_column]
        .max()
        .rename(columns={date_column: "Última Venda"})
    )

    label_map = _build_product_label_map(analytics)
    last_sale_df["Produto"] = last_sale_df["Código do Produto"].map(label_map).fillna(last_sale_df["Código do Produto"])

    today = pd.Timestamp.today().normalize()
    threshold = today - pd.DateOffset(months=3)
    last_sale_df["Dias sem venda"] = (today - last_sale_df["Última Venda"]).dt.days
    last_sale_df["Inativo > 3 meses"] = last_sale_df["Última Venda"] < threshold
    last_sale_df["Status"] = last_sale_df["Inativo > 3 meses"].map(
        {True: "Sem venda há mais de 3 meses", False: "Ativo"}
    )

    return (
        last_sale_df.sort_values(by=["Inativo > 3 meses", "Última Venda"], ascending=[False, True])
        .reset_index(drop=True)
    )


def _build_never_sold_products(
    sales_df: pd.DataFrame,
    analytics: SalesAnalytics | None,
) -> pd.DataFrame:
    """Builds a catalog list of products (ALL####) that never appeared in sales."""
    if analytics is None or getattr(analytics, "products_df", None) is None or analytics.products_df.empty:
        return pd.DataFrame(columns=["Código do Produto", "Descrição"])

    catalog_df = analytics.products_df.copy()
    if "Código" not in catalog_df.columns:
        return pd.DataFrame(columns=["Código do Produto", "Descrição"])

    catalog_df["Código do Produto"] = catalog_df["Código"].astype(str).str.strip().str.upper()
    catalog_df = catalog_df[catalog_df["Código do Produto"].str.match(VALID_PRODUCT_CODE_PATTERN, na=False)].copy()
    if catalog_df.empty:
        return pd.DataFrame(columns=["Código do Produto", "Descrição"])

    if "Descrição" not in catalog_df.columns:
        catalog_df["Descrição"] = catalog_df["Código do Produto"]
    else:
        catalog_df["Descrição"] = catalog_df["Descrição"].astype(str).str.strip()
        invalid_desc = catalog_df["Descrição"].str.lower().isin({"", "nan", "none", "n/a", "<na>"})
        catalog_df.loc[invalid_desc, "Descrição"] = catalog_df.loc[invalid_desc, "Código do Produto"]

    sold_codes = (
        sales_df.get("Código do Produto", pd.Series(dtype="object"))
        .astype(str)
        .str.strip()
        .str.upper()
    )
    sold_codes_set = set(sold_codes[sold_codes.str.match(VALID_PRODUCT_CODE_PATTERN, na=False)].tolist())

    never_sold_df = (
        catalog_df[["Código do Produto", "Descrição"]]
        .drop_duplicates(subset=["Código do Produto"], keep="first")
    )
    never_sold_df = never_sold_df[~never_sold_df["Código do Produto"].isin(sold_codes_set)].copy()
    return never_sold_df.sort_values(by=["Código do Produto"]).reset_index(drop=True)


def _render_never_sold_products_table(never_sold_df: pd.DataFrame) -> None:
    """Renders never sold products list below the last-sale section."""
    st.markdown("##### Produtos que Nunca Foram Vendidos")
    if never_sold_df.empty:
        st.info("Nenhum produto elegível sem venda encontrado.")
        return

    st.caption(f"{len(never_sold_df)} produto(s) do catálogo não possuem venda registrada no período filtrado.")
    st.dataframe(never_sold_df, hide_index=True, width="stretch")


def render_products(sales_df: pd.DataFrame, is_dark: bool, analytics: SalesAnalytics | None = None) -> None:
    """Renders product analytics including ranking, Pareto and ABC."""
    st.markdown("### Análise de Produtos")

    st.info("Nesta aba, todos os cálculos, listas e gráficos consideram apenas produtos com código no formato ALL + 4 dígitos (ex.: ALL1234).")

    eligible_sales_df = _filter_valid_all_products(sales_df)
    if eligible_sales_df.empty:
        st.warning("Nenhum produto no padrão ALL + 4 dígitos foi encontrado para os filtros atuais.")
        never_sold_df = _build_never_sold_products(eligible_sales_df, analytics)
        st.markdown("#### Última Venda por Produto")
        st.info("Sem vendas elegíveis para calcular última venda nos filtros atuais.")
        _render_never_sold_products_table(never_sold_df)
        return

    unique_products = int(eligible_sales_df["Código do Produto"].astype(str).nunique()) if "Código do Produto" in eligible_sales_df.columns else 0
    metric_card("Produtos Únicos Comercializados", f"{unique_products:,}", delta="Portfólio Ativo", delta_type="up")
    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)

    chart_container("Ranking de Produtos Mais Vendidos", "Selecione o limite de exibição")
    limit = st.radio("Quantidade de itens no ranking:", [10, 20], horizontal=True)

    products_abc_df, class_counts = SalesAnalytics.get_abc_pareto_analysis(eligible_sales_df)

    monthly_top_df, monthly_totals_df, top_product_codes, product_labels = _build_top_products_timeline(eligible_sales_df, analytics)

    if not monthly_top_df.empty and top_product_codes:
        top_product_order = [product_labels[code] for code in top_product_codes]
        color_map = _build_color_map(top_product_order)

        chart_container(
            "Evolução Mensal dos 5 Produtos Mais Vendidos",
            "Volume agregado por mês com barras agrupadas e participação no total do mês",
        )
        fig_monthly_volume = px.bar(
            monthly_top_df,
            x="Mês",
            y="Quantidade",
            color="Produto",
            category_orders={"Produto": top_product_order},
            color_discrete_map=color_map,
            custom_data=["Produto", "Participação (%)"],
            labels={"Mês": "Mês", "Quantidade": "Quantidade Vendida", "Produto": "Produto"},
        )
        fig_monthly_volume.update_traces(
            hovertemplate=(
                "Produto: %{customdata[0]}<br>"
                "Mês: %{x|%b/%Y}<br>"
                "Quantidade: %{y:,.0f}<br>"
                "Participação no mês: %{customdata[1]:.1f}%"
                "<extra></extra>"
            )
        )
        fig_monthly_volume.update_layout(get_plot_layout(is_dark))
        fig_monthly_volume.update_layout(
            barmode="group",
            height=430,
            margin=dict(l=40, r=40, t=25, b=55),
        )
        fig_monthly_volume.update_xaxes(tickformat="%b/%Y", title_text="Mês")
        fig_monthly_volume.update_yaxes(title_text="Quantidade Vendida")
        st.plotly_chart(fig_monthly_volume, width="stretch", config={"displayModeBar": False})
        chart_container_end()

        chart_container(
            "Participação Mensal dos 5 Produtos Mais Vendidos",
            "Percentual de cada produto dentro do volume total vendido no mês",
        )
        fig_monthly_share = px.bar(
            monthly_top_df,
            x="Mês",
            y="Participação (%)",
            color="Produto",
            category_orders={"Produto": top_product_order},
            color_discrete_map=color_map,
            custom_data=["Produto", "Quantidade"],
            labels={"Mês": "Mês", "Participação (%)": "Participação no Mês (%)", "Produto": "Produto"},
        )
        fig_monthly_share.update_traces(
            hovertemplate=(
                "Produto: %{customdata[0]}<br>"
                "Mês: %{x|%b/%Y}<br>"
                "Quantidade: %{customdata[1]:,.0f}<br>"
                "Participação no mês: %{y:.1f}%"
                "<extra></extra>"
            )
        )
        fig_monthly_share.update_layout(get_plot_layout(is_dark))
        fig_monthly_share.update_layout(
            barmode="group",
            height=300,
            margin=dict(l=40, r=40, t=25, b=55),
        )
        fig_monthly_share.update_xaxes(tickformat="%b/%Y", title_text="Mês")
        fig_monthly_share.update_yaxes(title_text="Participação no Mês (%)")
        st.plotly_chart(fig_monthly_share, width="stretch", config={"displayModeBar": False})
        chart_container_end()

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

    st.markdown("#### Última Venda por Produto")
    last_sale_df = _build_last_sale_list(eligible_sales_df, analytics)
    never_sold_df = _build_never_sold_products(eligible_sales_df, analytics)

    if last_sale_df.empty:
        st.info("Não foi possível montar a lista de última venda para os filtros atuais.")
    else:
        inactive_sold_count = int(last_sale_df["Inativo > 3 meses"].sum())
        sold_count = len(last_sale_df)
        never_sold_count = len(never_sold_df)
        total_count = sold_count + never_sold_count
        inactive_total_count = inactive_sold_count + never_sold_count
        inactive_pct = (inactive_total_count / total_count * 100) if total_count > 0 else 0.0

        kpi_col1, kpi_col2 = st.columns(2)
        with kpi_col1:
            metric_card(
                "Produtos Inativos (> 3 meses)",
                f"{inactive_pct:.1f}%",
                delta=f"{inactive_total_count} produto(s)",
                delta_type="warn" if inactive_total_count > 0 else "up",
            )
        with kpi_col2:
            metric_card(
                "Total de Produtos",
                f"{total_count:,}",
                delta=f"{never_sold_count} não comercializados",
                delta_type="up",
            )

        st.caption(
            f"{inactive_total_count} de {total_count} produtos estão inativos (inclui {never_sold_count} não comercializados e {inactive_sold_count} sem venda há mais de 3 meses)."
        )

        display_df = last_sale_df.copy()
        display_df["Última Venda"] = pd.to_datetime(display_df["Última Venda"], errors="coerce").dt.strftime("%d/%m/%Y")

        def _highlight_inactive(row: pd.Series) -> list[str]:
            if bool(row.get("Inativo > 3 meses")):
                return ["background-color: rgba(239, 68, 68, 0.12);"] * len(row)
            return [""] * len(row)

        styled_df = (
            display_df[["Produto", "Código do Produto", "Última Venda", "Dias sem venda", "Status", "Inativo > 3 meses"]]
            .style.apply(_highlight_inactive, axis=1)
            .hide(axis="columns", subset=["Inativo > 3 meses"])
        )
        st.dataframe(styled_df, hide_index=True, width="stretch")

    _render_never_sold_products_table(never_sold_df)

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
