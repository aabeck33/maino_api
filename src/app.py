"""
    Programa principal do aplicativo Streamlit para análise de vendas e insights gerenciais.
    Este aplicativo permite aos usuários visualizar e analisar dados de vendas, produtos,
    pedidos e informações fiscais a partir de uma planilha Excel. Ele oferece filtros interativos,
    exportação de dados e uma interface de usuário responsiva com suporte a temas claro e escuro.

Alvaro Adriano Beck - 07/2026
"""

import sys
import io
from pathlib import Path
import pandas as pd
import streamlit as st

from utils.logger import setup_logger
from analytics.processing import SalesAnalytics
from dashboard.components import apply_css, brand_header
from dashboard.views import (
    render_overview,
    render_products,
    render_orders,
    render_geography,
    render_fiscal,
    render_insights,
    render_representatives,
)

# Adjust system path to support absolute/package imports
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

# Caminho da Planilha de pedidos
PLANILHA_PEDIDOS = "pedidos_confirmados.xlsx"

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
def convert_df_to_excel(df: pd.DataFrame) -> bytes:
    """ Convert a DataFrame to an Excel file in memory and return as bytes.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dados Filtrados")
    return output.getvalue()

def main():
    """ Main function to run the Streamlit app.
    """
    # Load dataset
    excel_path = Path(__file__).resolve().parent.parent / "work" / PLANILHA_PEDIDOS

    try:
        analytics = SalesAnalytics(excel_path)
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

    # Apply Filters
    filtered_df = analytics.get_filtered_data(status_filter, product_search)
    kpis = analytics.calculate_kpis(filtered_df)

    # Export options in sidebar
    st.sidebar.markdown("---")
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

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"<p style='font-size:0.72rem;color:#71717a;text-align:center;'>Total Filtro: {len(filtered_df)} linhas</p>",
        unsafe_allow_html=True
    )

    # 6. Render Brand Header with theme switcher
    brand_header("Maino Business Intelligence", IS_DARK, toggle_theme)

    # 7. Navigation Tabs
    tabs = st.tabs([
        "📈 Visão Geral", 
        "👥 Representantes de Vendas",
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
        render_representatives(filtered_df, IS_DARK)

    with tabs[2]:
        render_products(filtered_df, IS_DARK)

    with tabs[3]:
        render_orders(filtered_df, IS_DARK)

    with tabs[4]:
        render_geography(filtered_df, IS_DARK)

    with tabs[5]:
        render_fiscal(filtered_df, IS_DARK)

    with tabs[6]:
        render_insights(filtered_df, kpis)

if __name__ == "__main__":
    main()
# streamlit run c:/Users/beck_/OneDrive/Documents/eclipse-workspace/Maino_API/src/app.py
