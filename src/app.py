"""
    Programa principal do aplicativo Streamlit para análise de vendas e insights gerenciais.
    Este aplicativo permite aos usuários visualizar e analisar dados de vendas, produtos,
    pedidos e informações fiscais a partir de uma planilha Excel. Ele oferece filtros interativos,
    exportação de dados e uma interface de usuário responsiva com suporte a temas claro e escuro.

    Documentação: https://changelog.maino.com.br/api-reference-maino/10.-pedidos-de-venda

Alvaro Adriano Beck - 07/2026
"""

import io
from pathlib import Path
import pandas as pd
import streamlit as st

from config.settings import SETTINGS
from utils.pdf_report import generate_executive_pdf
from utils.logger import setup_logger
from analytics.processing import SalesAnalytics
from dashboard.components import apply_css, brand_header
from dashboard.views_sections import (
    render_overview,
    render_products,
    render_orders,
    render_customers,
    render_geography,
    render_fiscal,
    render_insights,
    render_representatives,
    render_profitability,
)

logger = setup_logger("kpi_app")

# 1. Page Config
st.set_page_config(
    page_title="Painel de indicadores",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",  # Keep expanded for sidebar navigation & filters
)

# 2. Theme State Initializer
if "theme" not in st.session_state:
    st.session_state.theme = "light"

def toggle_theme():
    """ Toggle between light and dark themes.
    """
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

IS_DARK = st.session_state.theme == "dark"

# 3. Apply Unified Styling CSS
apply_css(IS_DARK)

# 4. In-Memory Excel converter for export
@st.cache_data(ttl=900, show_spinner=False)
def convert_df_to_excel(df: pd.DataFrame, sheet_name: str = "Dados Filtrados") -> bytes:
    """ Convert a DataFrame to an Excel file in memory and return as bytes.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


def _file_signature(path: Path) -> tuple[int, int]:
    """Builds a lightweight file signature for cache invalidation."""
    if not path.exists():
        return (0, 0)
    stat = path.stat()
    return (int(stat.st_mtime_ns), int(stat.st_size))


def _normalize_text_filter(value: str | None) -> str:
    """Normalizes text filters to keep cache signatures stable."""
    if value is None:
        return ""
    return str(value).strip().lower()


def _build_filter_signature(
    status_filter: str,
    product_search: str,
    representative_filter: str,
    customer_filter: str,
    region_filter: str,
    start_date,
    end_date,
) -> tuple:
    """Builds a hashable signature for global dashboard filters."""
    return (
        status_filter,
        _normalize_text_filter(product_search),
        representative_filter,
        _normalize_text_filter(customer_filter),
        str(region_filter).strip().upper(),
        start_date.isoformat() if start_date is not None else "",
        end_date.isoformat() if end_date is not None else "",
    )


@st.cache_resource(ttl=900, show_spinner=False)
def load_analytics_cached(
    sales_path_str: str,
    products_path_str: str,
    _sales_signature: tuple[int, int],
    _products_signature: tuple[int, int],
    _customers_signature: tuple[int, int],
) -> SalesAnalytics:
    """Caches the analytics facade and refreshes when source files change."""
    return SalesAnalytics(Path(sales_path_str), Path(products_path_str))

def main():
    """ Main function to run the Streamlit app.
    """
    logger.info("Iniciando renderizacao principal do dashboard")
    # Load dataset
    excel_path = SETTINGS.data_file_path(SETTINGS.data_files.sales_orders)
    products_excel_path = SETTINGS.data_file_path(SETTINGS.data_files.products)
    customers_excel_path = SETTINGS.data_file_path(SETTINGS.data_files.customers)

    try:
        analytics = load_analytics_cached(
            str(excel_path),
            str(products_excel_path),
            _file_signature(excel_path),
            _file_signature(products_excel_path),
            _file_signature(customers_excel_path),
        )
    except Exception as e:
        logger.error("Erro ao inicializar dados a partir do Excel: %s", e, exc_info=True)
        st.error(f"Não foi possível carregar a planilha de dados em: `{excel_path}`")
        st.exception(e)
        st.info("Execute o script de extração primeiro: `python src/export_orders.py`.")
        return

    # 5. Sidebar Menu & Filters (Menu lateral com filtros globais)
    st.sidebar.markdown("### 🛠️ Menu de Filtros")

    # Status NF Filter
    status_options = ["Todos", "Com NF Emitida", "Sem NF Emitida"]
    status_filter = st.sidebar.selectbox(
        "Status da Nota Fiscal:",
        options=status_options,
        index=0,
        help="Filtrar pedidos pela emissão de notas fiscais."
    )

    # Search Product Filter
    product_search = st.sidebar.text_input(
        "Pesquisar Produto (Código):",
        value="",
        placeholder="Ex: ALL1266",
        help="Filtra a base por partes do código do produto."
    )

    # Additional filters
    representative_options = ["Todos"] + sorted({str(value).strip() for value in analytics.df["Representante"].dropna() if str(value).strip()})
    representative_filter = st.sidebar.selectbox(
        "Representante:",
        options=representative_options,
        index=0,
        help="Filtrar pelos representantes de vendas presentes na base."
    )

    region_options = ["Todos"] + sorted({str(value).strip().upper() for value in analytics.df["UF"].dropna() if str(value).strip()})
    region_filter = st.sidebar.selectbox(
        "Região / UF:",
        options=region_options,
        index=0,
        help="Filtrar por unidade federativa."
    )

    customer_filter = st.sidebar.text_input(
        "Cliente (parcial):",
        value="",
        placeholder="Ex: ACME",
        help="Filtra por parte do nome ou chave do cliente."
    )

    start_date = st.sidebar.date_input("Data inicial", value=None)
    end_date = st.sidebar.date_input("Data final", value=None)

    filter_signature = _build_filter_signature(
        status_filter=status_filter,
        product_search=product_search,
        representative_filter=representative_filter,
        customer_filter=customer_filter,
        region_filter=region_filter,
        start_date=start_date,
        end_date=end_date,
    )

    previous_signature = st.session_state.get("_filters_signature")
    if previous_signature != filter_signature:
        filtered_df = analytics.get_filtered_data(
            status_filter,
            product_search,
            date_start=start_date,
            date_end=end_date,
            representative=representative_filter,
            customer=customer_filter,
            region=region_filter,
        )
        kpis = analytics.calculate_kpis(filtered_df)
        st.session_state["_filters_signature"] = filter_signature
        st.session_state["_filtered_df"] = filtered_df
        st.session_state["_kpis"] = kpis

        # Clear derived artifacts so they are rebuilt only when explicitly requested.
        st.session_state.pop("_profitability_df", None)
        st.session_state.pop("_prepared_filtered_export_key", None)
        st.session_state.pop("_prepared_profitability_export_key", None)
        st.session_state.pop("_filtered_export_bytes", None)
        st.session_state.pop("_profitability_export_bytes", None)
        st.session_state.pop("_profitability_artifacts", None)
        st.session_state.pop("_profitability_artifacts_signature", None)
    else:
        filtered_df = st.session_state.get("_filtered_df", pd.DataFrame())
        kpis = st.session_state.get("_kpis", analytics.calculate_kpis(filtered_df))

    profitability_df: pd.DataFrame | None = st.session_state.get("_profitability_df")
    profitability_artifacts: dict | None = st.session_state.get("_profitability_artifacts")

    def get_profitability_df() -> pd.DataFrame:
        nonlocal profitability_df
        if profitability_df is None:
            profitability_df = analytics.build_profitability_dataset(filtered_df)
            st.session_state["_profitability_df"] = profitability_df
        return profitability_df

    def get_profitability_artifacts() -> dict:
        nonlocal profitability_artifacts

        cached_signature = st.session_state.get("_profitability_artifacts_signature")
        if profitability_artifacts is not None and cached_signature == filter_signature:
            return profitability_artifacts

        profitability_source_df = get_profitability_df()
        unified_revenue_total = analytics.calculate_total_revenue(filtered_df)
        financial_kpis = analytics.calculate_financial_kpis(
            profitability_source_df,
            revenue_total_override=unified_revenue_total,
        )
        product_profitability_df = analytics.get_profitability_by_product(profitability_source_df)
        representative_profitability_df = analytics.get_profitability_by_representative(profitability_source_df)
        customer_profitability_df = analytics.get_profitability_by_customer(profitability_source_df)
        monthly_profitability_df = analytics.get_monthly_profitability(profitability_source_df)
        abc_revenue_df, _ = analytics.get_abc_analysis(product_profitability_df, "Faturamento")
        abc_profit_df, _ = analytics.get_abc_analysis(product_profitability_df, "Margem de contribuição")

        profitability_artifacts = {
            "financial_kpis": financial_kpis,
            "product_profitability_df": product_profitability_df,
            "representative_profitability_df": representative_profitability_df,
            "customer_profitability_df": customer_profitability_df,
            "monthly_profitability_df": monthly_profitability_df,
            "abc_revenue_df": abc_revenue_df,
            "abc_profit_df": abc_profit_df,
        }
        st.session_state["_profitability_artifacts"] = profitability_artifacts
        st.session_state["_profitability_artifacts_signature"] = filter_signature
        return profitability_artifacts


    # Botão para imprimir o PDF
    #st.sidebar.divider()
    st.sidebar.markdown("### Relatórios")
    if st.sidebar.button(
            "📄 Gerar PDF",
            use_container_width=True
        ):
        profitability_df_for_pdf = get_profitability_df()
        profitability_derived = get_profitability_artifacts()
        representative_performance_df = analytics.get_representative_performance(filtered_df)
        state_ticket_df = analytics.get_state_ticket_average(filtered_df)

        pdf_file = generate_executive_pdf(
            analytics,
            filtered_df,
            profitability_df=profitability_df_for_pdf,
            core_kpis=kpis,
            financial_kpis=profitability_derived["financial_kpis"],
            monthly_profitability_df=profitability_derived["monthly_profitability_df"],
            product_profitability_df=profitability_derived["product_profitability_df"],
            representative_performance_df=representative_performance_df,
            state_ticket_df=state_ticket_df,
        )
        with open(pdf_file, "rb") as f:
            st.sidebar.download_button(
                label="⬇️ Baixar PDF",
                data=f,
                file_name="relatorio_gerencial.pdf",
                mime="application/pdf"
            )

    # Export options in sidebar
    #st.sidebar.markdown("---")
    st.sidebar.markdown("### 📥 Exportação")

    if not filtered_df.empty:
        if st.sidebar.button("🧮 Preparar Excel de Dados Filtrados", use_container_width=True):
            try:
                st.session_state["_filtered_export_bytes"] = convert_df_to_excel(filtered_df)
                st.session_state["_prepared_filtered_export_key"] = filter_signature
            except Exception as e:
                logger.error("Erro ao preparar exportação para Excel: %s", e, exc_info=True)
                st.sidebar.warning("Erro ao preparar botão de exportação.")

        if st.session_state.get("_prepared_filtered_export_key") == filter_signature:
            filtered_export_bytes = st.session_state.get("_filtered_export_bytes")
            if filtered_export_bytes:
                st.sidebar.download_button(
                    label="📄 Exportar Dados Filtrados (Excel)",
                    data=filtered_export_bytes,
                    file_name="dados_filtrados_maino.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
    else:
        st.sidebar.info("Nenhum dado filtrado para exportar.")

    if st.sidebar.button("🧮 Preparar Excel de Rentabilidade", use_container_width=True):
        try:
            profitability_bytes = convert_df_to_excel(get_profitability_df(), sheet_name="Rentabilidade")
            st.session_state["_profitability_export_bytes"] = profitability_bytes
            st.session_state["_prepared_profitability_export_key"] = filter_signature
        except Exception as e:
            logger.error("Erro ao preparar exportação de rentabilidade: %s", e, exc_info=True)
            st.sidebar.warning("Erro ao preparar botão de exportação financeira.")

    if st.session_state.get("_prepared_profitability_export_key") == filter_signature:
        profitability_export_bytes = st.session_state.get("_profitability_export_bytes")
        if profitability_export_bytes:
            st.sidebar.download_button(
                label="📈 Exportar Indicadores de Rentabilidade (Excel)",
                data=profitability_export_bytes,
                file_name="indicadores_financeiros.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    #st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"<p style='font-size:0.72rem;color:#71717a;text-align:center;'>Total Filtro: {len(filtered_df)} linhas</p>",
        unsafe_allow_html=True
    )

    # 6. Render Brand Header with theme switcher
    brand_header("Maino Business Intelligence", IS_DARK, toggle_theme)

    # 7. Navigation Tabs
    tabs = st.tabs([
        "📈 Visão Geral", 
        "💰 Rentabilidade",
        "👥 Representantes de Vendas",
        "👥 Clientes",
        "📦 Produtos", 
        "🛒 Pedidos", 
        "🌍 Geo", 
        "⚖️ Fiscal", 
        "💡 Insights Gerenciais"
    ], on_change="rerun")

    # Handle view rendering per tab
    if tabs[0].open:
        with tabs[0]:
            render_overview(filtered_df, kpis, analytics=analytics)

    if tabs[1].open:
        with tabs[1]:
            render_profitability(
                filtered_df,
                get_profitability_df(),
                IS_DARK,
                analytics=analytics,
                profitability_artifacts=get_profitability_artifacts(),
            )

    if tabs[2].open:
        with tabs[2]:
            render_representatives(filtered_df, IS_DARK)

    if tabs[3].open:
        with tabs[3]:
            render_customers(filtered_df)

    if tabs[4].open:
        with tabs[4]:
            render_products(filtered_df, IS_DARK)

    if tabs[5].open:
        with tabs[5]:
            render_orders(filtered_df, IS_DARK)

    if tabs[6].open:
        with tabs[6]:
            render_geography(filtered_df, IS_DARK)

    if tabs[7].open:
        with tabs[7]:
            render_fiscal(filtered_df, IS_DARK)

    if tabs[8].open:
        with tabs[8]:
            render_insights(filtered_df, kpis)

main()
# streamlit run c:/Users/beck_/OneDrive/Documents/eclipse-workspace/Maino_API/src/app.py
