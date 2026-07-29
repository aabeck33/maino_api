import streamlit as st
import streamlit.components.v1 as components
from typing import Optional, List
import pandas as pd

def apply_css(is_dark: bool) -> None:
    """Injects custom CSS to style the app according to the Unified Design System."""

    # Swapping colors based on active theme
    bg = "#09090b" if is_dark else "#ffffff"
    bg_subtle = "#0b1220" if is_dark else "#f8fafc"
    card = "#0c0c0f" if is_dark else "#ffffff"
    card_hover = "#131316" if is_dark else "#f4f4f5"
    border = "#1e1e24" if is_dark else "#e4e4e7"
    border_subtle = "#16161a" if is_dark else "#f0f0f2"
    text = "#fafafa" if is_dark else "#09090b"
    text_muted = "#71717a"
    text_dim = "#52525b" if is_dark else "#a1a1aa"
    accent = "#2563eb"
    green = "#22c55e" if is_dark else "#16a34a"
    green_muted = "rgba(34,197,94,0.12)" if is_dark else "rgba(22,163,74,0.08)"
    red = "#ef4444" if is_dark else "#dc2626"
    red_muted = "rgba(239,68,68,0.12)" if is_dark else "rgba(220,38,38,0.08)"
    amber = "#f59e0b" if is_dark else "#d97706"
    amber_muted = "rgba(245,158,11,0.12)" if is_dark else "rgba(217,119,6,0.08)"
    shadow = "none" if is_dark else "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03)"
    
    # ==========================================
    # CSS ESPECÍFICO PARA CADA TEMA
    # ==========================================
    if is_dark:
        theme_css = """
        /* =========================
        SELECT / DROPDOWN
        ========================= */
        div[role="listbox"] {
            background: #18181b !important;
            color: #fafafa !important;
            border: 1px solid #27272a !important;
            border-radius: 10px !important;
            box-shadow: 0 6px 18px rgba(0,0,0,0.45) !important;
        }

        div[role="option"] {
            background: #18181b !important;
            color: #fafafa !important;
        }

        div[role="option"]:hover {
            background: #27272a !important;
        }

        div[role="option"][aria-selected="true"] {
            background: #3f3f46 !important;
            color: #ffffff !important;
            font-weight: 500 !important;
        }

        /* =========================
        BASEWEB SELECT
        ========================= */
        [data-baseweb="select"] {
            background: #18181b !important;
            border-radius: 10px !important;
        }

        [data-baseweb="select"] * {
            color: #fafafa !important;
        }

        [data-baseweb="select"] > div {
            background: #18181b !important;
        }

        [data-baseweb="select"] svg,
        [data-baseweb="popover"] svg,
        .stSelectbox svg {
            color: #d4d4d8 !important;
            fill: #d4d4d8 !important;
            opacity: 1 !important;
        }

        /* =========================
        INPUTS
        ========================= */
        input,
        textarea {
            background: #18181b !important;
            color: #fafafa !important;
            border: 1px solid #27272a !important;
        }

        input:focus,
        textarea:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 2px rgba(59,130,246,0.20) !important;
        }

        /* =========================
        DOWNLOAD BUTTON
        ========================= */
        .stDownloadButton button {
            background: #18181b !important;
            color: #fafafa !important;
            border: 1px solid #27272a !important;
            border-radius: 12px !important;
            transition: all 0.20s ease-in-out !important;
            font-weight: 500 !important;
        }

        .stDownloadButton button:hover {
            background: #27272a !important;
            border-color: #52525b !important;
        }

        .stDownloadButton button:focus {
            outline: none !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.20) !important;
        }

        /* =========================
        BOTÕES STREAMLIT
        ========================= */
        .stButton button {
            background: #18181b !important;
            color: #fafafa !important;
            border: 1px solid #27272a !important;
            border-radius: 12px !important;
            transition: all 0.20s ease-in-out !important;
        }

        .stButton button:hover {
            background: #27272a !important;
            border-color: #52525b !important;
        }

        .stButton button:focus {
            outline: none !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.20) !important;
        }

        /* =========================
        DATAFRAME
        ========================= */
        [data-testid="stDataFrame"] {
            border: 1px solid #27272a !important;
            border-radius: 12px !important;
        }

        /* =========================
        SCROLLBAR
        ========================= */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: #18181b;
        }

        ::-webkit-scrollbar-thumb {
            background: #3f3f46;
            border-radius: 8px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #52525b;
        }

        /* =========================
        TOOLTIPS / POPUPS
        ========================= */
        [data-baseweb="tooltip"] {
            background: #09090b !important;
            color: #fafafa !important;
            border: 1px solid #27272a !important;
        }
        """
    else:
        theme_css = """
        /* =========================
        SELECT / DROPDOWN
        ========================= */
        div[role="listbox"] {
            background: #ffffff !important;
            color: #09090b !important;
            border: 1px solid #d4d4d8 !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        }

        div[role="option"] {
            background: #ffffff !important;
            color: #09090b !important;
        }

        div[role="option"]:hover {
            background: #f4f4f5 !important;
        }

        div[role="option"][aria-selected="true"] {
            background: #e4e4e7 !important;
            color: #09090b !important;
            font-weight: 500 !important;
        }

        /* =========================
        BASEWEB SELECT
        ========================= */
        [data-baseweb="select"] {
            background: #ffffff !important;
            border-radius: 10px !important;
        }

        [data-baseweb="select"] * {
            color: #09090b !important;
        }

        [data-baseweb="select"] svg,
        [data-baseweb="popover"] svg {
            color: #52525b !important;
            fill: #52525b !important;
            opacity: 1 !important;
        }

        [data-baseweb="select"] > div {
            background: #ffffff !important;
        }

        [data-baseweb="select"] > div:last-child {
            background: transparent !important;
        }

        /* =========================
            ARROW FIX
        ========================= */
        .stSelectbox svg,
        [data-baseweb="select"] svg,
        [data-baseweb="popover"] svg {
            color: #27272a !important;
            fill: #27272a !important;
            stroke: #27272a !important;
            opacity: 1 !important;
        }

        .stSelectbox svg path,
        [data-baseweb="select"] svg path,
        [data-baseweb="popover"] svg path {
            fill: #27272a !important;
            stroke: #27272a !important;
        }

        /* =========================
        INPUTS
        ========================= */
        input,
        textarea {
            background: #ffffff !important;
            color: #09090b !important;
            border: 1px solid #d4d4d8 !important;
        }

        input:focus,
        textarea:focus {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 2px rgba(37,99,235,0.15) !important;
        }

        /* =========================
        DOWNLOAD BUTTON
        ========================= */
        .stDownloadButton button {
            background: #ffffff !important;
            color: #09090b !important;
            border: 1px solid #d4d4d8 !important;
            border-radius: 12px !important;
            transition: all 0.20s ease-in-out !important;
            font-weight: 500 !important;
        }

        .stDownloadButton button:hover {
            background: #f4f4f5 !important;
            border-color: #a1a1aa !important;
        }

        .stDownloadButton button:focus {
            outline: none !important;
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37,99,235,0.20) !important;
        }

        /* =========================
        BOTÕES STREAMLIT
        ========================= */
        .stButton button {
            background: #ffffff !important;
            color: #09090b !important;
            border: 1px solid #d4d4d8 !important;
            border-radius: 12px !important;
            transition: all 0.20s ease-in-out !important;
        }

        .stButton button:hover {
            background: #f4f4f5 !important;
            border-color: #a1a1aa !important;
        }

        .stButton button:focus {
            outline: none !important;
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37,99,235,0.20) !important;
        }

        /* =========================
        DATAFRAME
        ========================= */
        [data-testid="stDataFrame"] {
            border: 1px solid #e4e4e7 !important;
            border-radius: 12px !important;
        }

        /* =========================
        SCROLLBAR
        ========================= */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: #f4f4f5;
        }

        ::-webkit-scrollbar-thumb {
            background: #a1a1aa;
            border-radius: 8px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #71717a;
        }

        /* ==========================================
        SETA DOS COMBOBOXES
        ========================================== */
        [data-baseweb="select"] svg {
            color: #27272a !important;
            fill: #27272a !important;
            stroke: #27272a !important;
            opacity: 1 !important;
        }

        [data-baseweb="select"] path {
            fill: #27272a !important;
            stroke: #27272a !important;
        }
        """

    css = f"""
    <style>
        /* Unified Theme variables */
        :root {{
            --bg: {bg};
            --bg-subtle: {bg_subtle};
            --card: {card};
            --card-hover: {card_hover};
            --border: {border};
            --border-subtle: {border_subtle};
            --text: {text};
            --text-muted: {text_muted};
            --text-dim: {text_dim};
            --accent: {accent};
            --green: {green};
            --green-muted: {green_muted};
            --red: {red};
            --red-muted: {red_muted};
            --amber: {amber};
            --amber-muted: {amber_muted};
            --shadow: {shadow};
            --radius: 10px;
        }}

        /* ==================================================
        FOUNDATION
        ================================================== */
        * {{
            box-sizing: border-box;
        }}

        html,
        body,
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        .main,
        .block-container,
        section[data-testid="stMain"] {{
            background: var(--bg) !important;
            color: var(--text) !important;
            font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
        }}

        /* ==================================================
        STREAMLIT CLEANUP
        ================================================== */
        header[data-testid="stHeader"],
        #MainMenu,
        footer,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        .stDeployButton,
        [data-testid="stSidebarCollapsedControl"] {{
            display: none !important;
        }}

        /* ==================================================
        SIDEBAR
        ================================================== */
        [data-testid="stSidebar"] {{
            background: var(--bg-subtle) !important;
            border-right: 1px solid var(--border) !important;
        }}

        [data-testid="stSidebar"] * {{
            color: var(--text) !important;
        }}

        section[data-testid="stSidebar"] .stTextInput,
        section[data-testid="stSidebar"] .stSelectbox,
        section[data-testid="stSidebar"] .stDateInput {{
            margin-bottom: -6px;
        }}

        section[data-testid="stSidebar"] label {{
            margin-bottom: 2px !important;
        }}

        section[data-testid="stSidebar"] .stButton > button {{
            width: 100%;
            height: 48px;
            font-weight: 600;
            border-radius: 12px;
        }}

        /* ==================================================
        LAYOUT
        ================================================== */
        .block-container {{
            max-width: 1500px !important;
            padding: 2rem 2.8rem !important;
        }}

        [data-testid="stHorizontalBlock"] {{
            gap: 1.25rem !important;
        }}

        /* ==================================================
        TYPOGRAPHY
        ================================================== */
        h1,
        h2,
        h3,
        h4,
        h5,
        h6 {{
            color: var(--text) !important;
            letter-spacing: -0.03em;
        }}

        p,
        span,
        label,
        li,
        td,
        th {{
            color: var(--text) !important;
        }}

        /* ==================================================
        TABS
        ================================================== */
        button[data-baseweb="tab"] {{
            background: transparent !important;
            color: var(--text-muted) !important;
            border-radius: 8px !important;
            padding: 0.65rem 1.3rem !important;
            font-weight: 500 !important;
            border: 1px solid transparent !important;
            transition: all 0.18s ease !important;
        }}

        button[data-baseweb="tab"]:hover {{
            background: var(--card-hover) !important;
            color: var(--text) !important;
        }}

        button[data-baseweb="tab"][aria-selected="true"] {{
            background: var(--card) !important;
            color: var(--text) !important;
            border-color: var(--border) !important;
            font-weight: 600 !important;
        }}

        [data-baseweb="tab-highlight"],
        [data-baseweb="tab-border"] {{
            display: none !important;
        }}

        [data-baseweb="tab-list"] {{
            background: var(--bg-subtle) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 4px !important;
            gap: 4px !important;
            margin-bottom: 1.5rem !important;
        }}

        /* ==================================================
        INPUTS
        ================================================== */
        .stTextInput input,
        .stNumberInput input,
        .stDateInput input,
        textarea {{
            border-radius: 12px !important;
            border: 1px solid var(--border) !important;
        }}

        .stTextInput input:focus,
        .stNumberInput input:focus,
        .stDateInput input:focus,
        textarea:focus {{
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 3px rgba(37,99,235,0.15) !important;
        }}

        /* ==================================================
        SURFACES
        ================================================== */
        .metric-card,
        .chart-wrap,
        .table-wrap {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            box-shadow: var(--shadow);
        }}

        .metric-card {{
            padding: 1.25rem 1.4rem;
            transition:
                transform 0.18s ease,
                border-color 0.18s ease,
                box-shadow 0.18s ease;
        }}

        .metric-card:hover {{
            transform: translateY(-3px);
            border-color: var(--accent);
        }}

        .chart-wrap,
        .table-wrap {{
            padding: 1.4rem;
            margin-bottom: 1.25rem;
        }}

        /* ==================================================
        METRICS
        ================================================== */
        .metric-label {{
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .metric-value {{
            font-size: 1.85rem;
            font-weight: 700;
            color: var(--text);
            margin-top: 0.2rem;
            letter-spacing: -0.03em;
        }}

        .metric-delta {{
            margin-top: 0.4rem;
            padding: 3px 8px;
            border-radius: 6px;
            display: inline-flex;
            gap: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .delta-up {{
            color: var(--green);
            background: var(--green-muted);
        }}

        .delta-down {{
            color: var(--red);
            background: var(--red-muted);
        }}

        .delta-warn {{
            color: var(--amber);
            background: var(--amber-muted);
        }}

        /* ==================================================
        CHARTS
        ================================================== */
        .chart-header {{
            margin-bottom: 1rem;
        }}

        .chart-title {{
            font-size: 0.9rem;
            font-weight: 600;
        }}

        .chart-subtitle {{
            font-size: 0.76rem;
            color: var(--text-dim);
        }}

        /* ==================================================
        TABLES
        ================================================== */
        .data-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.82rem;
        }}

        .data-table th {{
            background: var(--bg-subtle);
            color: var(--text-muted);
            padding: 0.8rem;
            text-align: left;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 2px solid var(--border);
        }}

        .data-table td {{
            padding: 0.8rem;
            border-bottom: 1px solid var(--border-subtle);
        }}

        .data-table tr {{
            transition: background-color 0.15s ease;
        }}

        .data-table tr:hover td {{
            background: var(--bg-subtle);
        }}

        .data-table tr:last-child td {{
            border-bottom: none;
        }}

        /* ==================================================
        BADGES
        ================================================== */
        .badge {{
            display: inline-block;
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 600;
        }}

        .badge-green {{
            background: var(--green-muted);
            color: var(--green);
        }}

        .badge-red {{
            background: var(--red-muted);
            color: var(--red);
        }}

        .badge-amber {{
            background: var(--amber-muted);
            color: var(--amber);
        }}

        .badge-blue {{
            background: rgba(37,99,235,0.12);
            color: var(--accent);
        }}

        /* ==================================================
        BRAND
        ================================================== */
        .brand-wrap {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
        }}

        .brand-title {{
            font-size: 1.45rem;
            font-weight: 700;
            color: var(--text);
        }}

        .brand-subtitle {{
            margin-top: 0.2rem;
            color: var(--text-muted);
            font-size: 0.8rem;
        }}

        /* ==================================================
        INSIGHTS
        ================================================== */
        .insight-card {{
            background: var(--bg-subtle);
            border-left: 4px solid var(--accent);
            border-radius: 8px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
        }}

        .insight-title {{
            font-size: 0.85rem;
            font-weight: 600;
        }}

        .insight-desc {{
            margin-top: 0.3rem;
            color: var(--text-muted);
            font-size: 0.8rem;
            line-height: 1.5;
        }}

        /* ==================================================
        DATAFRAME
        ================================================== */
        [data-testid="stDataFrame"] {{
            border-radius: 12px !important;
            overflow: hidden;
        }}

        /* ==================================================
        SCROLLBAR
        ================================================== */
        ::-webkit-scrollbar {{
            width: 10px;
            height: 10px;
        }}

        ::-webkit-scrollbar-track {{
            background: var(--bg-subtle);
        }}

        ::-webkit-scrollbar-thumb {{
            background: var(--border);
            border-radius: 8px;
        }}

        ::-webkit-scrollbar-thumb:hover {{
            background: var(--text-dim);
        }}

        {theme_css}

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def metric_card(label: str, value: str, delta: Optional[str] = None, delta_type: str = "up") -> None:
    """Renders a custom executive KPI card."""
    cls = f"delta-{delta_type}"
    arrow = "↑" if delta_type == "up" else ("↓" if delta_type == "down" else "→")
    delta_html = f'<div class="metric-delta {cls}">{arrow} {delta}</div>' if delta else ""
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def brand_header(title: str, is_dark: bool, toggle_callback) -> None:
    """Renders the executive branding header with title, subtitle and theme toggle."""
    col_left, col_theme, col_sidebar = st.columns([5, 1, 1])
    with col_left:
        st.markdown(f"""
        <div class="brand-wrap-inline">
            <div class="brand-title">📊 {title}</div>
            <div class="brand-subtitle">Dashboard Executivo de Inteligência de Vendas e Notas Fiscais</div>
        </div>
        """, unsafe_allow_html=True)
    with col_theme:
        theme_label = ("☀️ Modo Claro"
            if is_dark
            else "🌙 Modo Escuro"
        )
        st.button(
            theme_label,
            on_click=toggle_callback,
            use_container_width=True
        )
    with col_sidebar:
        if st.button("🧭 Restore Sidebar"):
            components.html(
                """
                <script>
                localStorage.setItem(
                    "stSidebarCollapsed-",
                    false
                );
                window.parent.location.reload();
                </script>
                """,
                height=0,
            )
        
    st.markdown("<hr style='margin: 0.5rem 0 1.5rem 0; border: 0; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)

def custom_table(df: pd.DataFrame, columns_mapping: dict) -> None:
    """Renders a custom HTML/CSS data table matching the design system."""
    if df.empty:
        st.markdown("<p style='font-size: 0.8rem; color: var(--text-muted);'>Nenhum dado disponível.</p>", unsafe_allow_html=True)
        return
        
    # Build headers
    headers_html = "".join(f"<th>{columns_mapping.get(col, col)}</th>" for col in df.columns)
    
    # Build rows
    rows_html = ""
    for _, row in df.iterrows():
        cells = ""
        for col in df.columns:
            val = row[col]
            # Badge rendering for Status da Nota Fiscal
            if col == "Status da Nota Fiscal":
                badge_class = "badge-green" if val == "ACEITA" else ("badge-red" if val == "Não emitida" else "badge-amber")
                cell_val = f'<span class="badge {badge_class}">{val}</span>'
            # Badge rendering for ABC Curve
            elif col == "Classe ABC":
                badge_class = "badge-blue" if val == "A" else ("badge-amber" if val == "B" else "badge-green")
                cell_val = f'<span class="badge {badge_class}">Classe {val}</span>'
            # Formatting numeric floats
            elif isinstance(val, float):
                if "Percentual" in col or "Participação" in col or "Acumulado (%)" in col:
                    cell_val = f"{val:.2f}%"
                else:
                    cell_val = f"{val:,.2f}"
            else:
                cell_val = str(val)
                
            cells += f"<td>{cell_val}</td>"
        rows_html += f"<tr>{cells}</tr>"
        
    st.markdown(f"""
    <div class="table-wrap">
        <table class="data-table">
            <thead>
                <tr>{headers_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

def chart_container(title: str, subtitle: str = "") -> None:
    """Helper to open a styled visual card wrapper around a chart."""
    subtitle_html = f'<div class="chart-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div class="chart-wrap">
        <div class="chart-header">
            <div class="chart-title">{title}</div>
            {subtitle_html}
        </div>
    """, unsafe_allow_html=True)

def chart_container_end() -> None:
    """Closes the styled visual card wrapper around a chart."""
    st.markdown("</div>", unsafe_allow_html=True)
