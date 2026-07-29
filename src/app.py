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

logger = setup_logger("maino_app")

# 1. Page Config
st.set_page_config(
    page_title="Maino Executivo",
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
def convert_df_to_excel(df: pd.DataFrame, sheet_name: str = "Dados Filtrados") -> bytes:
    """ Convert a DataFrame to an Excel file in memory and return as bytes.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

def main():
    """ Main function to run the Streamlit app.
    """
    # Load dataset
    excel_path = SETTINGS.data_file_path(SETTINGS.data_files.sales_orders)
    products_excel_path = SETTINGS.data_file_path(SETTINGS.data_files.products)

    try:
        analytics = SalesAnalytics(excel_path, products_excel_path)
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

    # Apply Filters
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
    profitability_df = analytics.build_profitability_dataset(filtered_df)

    if not profitability_df.empty:
        profitability_output_path = SETTINGS.data_file_path(SETTINGS.data_files.profitability_output)
        profitability_output_path.parent.mkdir(parents=True, exist_ok=True)
        profitability_df.to_excel(profitability_output_path, index=False, sheet_name="Rentabilidade")
        logger.info("Arquivo de rentabilidade exportado para %s", profitability_output_path)

        product_summary = analytics.get_profitability_by_product(profitability_df)
        rep_summary = analytics.get_profitability_by_representative(profitability_df)
        customer_summary = analytics.get_profitability_by_customer(profitability_df)
        summary_output_path = SETTINGS.data_file_path(SETTINGS.data_files.profitability_summary_output)
        with pd.ExcelWriter(summary_output_path) as writer:
            product_summary.to_excel(writer, sheet_name="Produtos", index=False)
            rep_summary.to_excel(writer, sheet_name="Representantes", index=False)
            customer_summary.to_excel(writer, sheet_name="Clientes", index=False)
        logger.info("Resumo financeiro exportado para %s", summary_output_path)


    # Botão para imprimir o PDF
    #st.sidebar.divider()
    st.sidebar.markdown("### Relatórios")
    if st.sidebar.button(
            "📄 Gerar PDF",
            use_container_width=True
        ):
        financial_kpis = analytics.calculate_financial_kpis(profitability_df)
        monthly_profitability_df = analytics.get_monthly_profitability(profitability_df)
        product_profitability_df = analytics.get_profitability_by_product(profitability_df)
        representative_performance_df = analytics.get_representative_performance(filtered_df)
        state_ticket_df = analytics.get_state_ticket_average(filtered_df)

        pdf_file = generate_executive_pdf(
            analytics,
            filtered_df,
            profitability_df=profitability_df,
            core_kpis=kpis,
            financial_kpis=financial_kpis,
            monthly_profitability_df=monthly_profitability_df,
            product_profitability_df=product_profitability_df,
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
        try:
            excel_bytes = convert_df_to_excel(filtered_df)
            st.sidebar.download_button(
                label="📄 Exportar Dados Filtrados (Excel)",
                data=excel_bytes,
                file_name="dados_filtrados_maino.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            logger.error("Erro ao preparar exportação para Excel: %s", e, exc_info=True)
            st.sidebar.warning("Erro ao preparar botão de exportação.")
    else:
        st.sidebar.info("Nenhum dado filtrado para exportar.")

    if not profitability_df.empty:
        try:
            profitability_bytes = convert_df_to_excel(profitability_df, sheet_name="Rentabilidade")
            st.sidebar.download_button(
                label="📈 Exportar Indicadores de Rentabilidade (Excel)",
                data=profitability_bytes,
                file_name="indicadores_financeiros.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            logger.error("Erro ao preparar exportação de rentabilidade: %s", e, exc_info=True)
            st.sidebar.warning("Erro ao preparar botão de exportação financeira.")

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
    ])

    # Handle view rendering per tab
    with tabs[0]:
        render_overview(filtered_df, kpis)

    with tabs[1]:
        render_profitability(filtered_df, profitability_df, IS_DARK)

    with tabs[2]:
        render_representatives(filtered_df, IS_DARK)

    with tabs[4]:
        render_products(filtered_df, IS_DARK)

    with tabs[5]:
        render_orders(filtered_df, IS_DARK)

    with tabs[6]:
        render_geography(filtered_df, IS_DARK)

    with tabs[7]:
        render_fiscal(filtered_df, IS_DARK)

    with tabs[8]:
        render_insights(filtered_df, kpis)
    
    with tabs[3]:
        render_customers(filtered_df)

if __name__ == "__main__":
    main()
# streamlit run c:/Users/beck_/OneDrive/Documents/eclipse-workspace/Maino_API/src/app.py
