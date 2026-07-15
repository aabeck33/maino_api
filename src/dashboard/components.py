import streamlit as st
from typing import Optional, List
import pandas as pd

def apply_css(is_dark: bool) -> None:
    """Injects custom CSS to style the app according to the Unified Design System."""
    
    # Swapping colors based on active theme
    bg = "#09090b" if is_dark else "#ffffff"
    bg_subtle = "#0c0c0f" if is_dark else "#f9fafb"
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

        /* Hide default Streamlit visual headers & footers for standalone app feel */
        header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"],
        [data-testid="stDecoration"], [data-testid="stStatusWidget"], .stDeployButton,
        div[data-testid="stSidebarCollapsedControl"] {{
            display: none !important;
        }}

        /* Sidebar styling adjustments */
        [data-testid="stSidebar"] {{
            background-color: var(--bg-subtle) !important;
            color: var(--text) !important;
        }}
        [data-testid="stSidebar"] * {{
            color: var(--text) !important;
        }}
        [data-testid="stSidebar"] a,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] button {{
            color: var(--text) !important;
        }}

        /* Application Layout */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container, section[data-testid="stMain"] {{
            background-color: var(--bg) !important;
            color: var(--text) !important;
            font-family: 'DM Sans', -apple-system, sans-serif !important;
        }}

        /* Ensure text in light theme is always readable */
        [data-testid="stAppViewContainer"] *,
        .stMarkdown, .stMarkdown *,
        .stText, .stText *,
        .stButton>button,
        button,
        label,
        a,
        span,
        li,
        td,
        th,
        p,
        div,
        h1,
        h2,
        h3,
        h4,
        h5,
        h6 {{
            color: var(--text) !important;
        }}

        .stButton>button,
        input,
        select,
        textarea,
        .stTextInput>div,
        .stNumberInput>div,
        .stSelectbox>div,
        .stCheckbox, .stRadio {{
            color: var(--text) !important;
            background-color: var(--card) !important;
            border-color: var(--border) !important;
        }}

        .block-container {{
            padding: 2.5rem 3rem !important;
            max-width: 1400px !important;
            margin: 0 auto;
        }}

        /* Horizontal Layout blocks gaps */
        [data-testid="stHorizontalBlock"] {{
            gap: 1.25rem !important;
        }}
        [data-testid="stVerticalBlock"] > div:has(> [data-testid="stHorizontalBlock"]) {{
            margin-bottom: 0.5rem !important;
        }}

        /* Navigation Tab custom styling (pill-style) */
        button[data-baseweb="tab"] {{
            background: transparent !important;
            color: var(--text-muted) !important;
            font-size: 0.85rem !important;
            font-weight: 500 !important;
            padding: 0.55rem 1.2rem !important;
            border: 1px solid transparent !important;
            border-radius: 7px !important;
            transition: all 0.2s ease-in-out;
        }}
        button[data-baseweb="tab"]:hover {{
            color: var(--text) !important;
            background: var(--card-hover) !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: var(--text) !important;
            background: var(--card) !important;
            border-color: var(--border) !important;
        }}
        [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{
            display: none !important;
        }}
        [data-baseweb="tab-list"] {{
            gap: 4px !important;
            background: var(--bg-subtle) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            padding: 4px !important;
            margin-bottom: 1.5rem !important;
        }}

        /* Card components styling */
        .metric-card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.25rem 1.4rem;
            box-shadow: var(--shadow);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border-color: var(--accent);
        }}
        .metric-label {{
            font-size: 0.78rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .metric-value {{
            font-size: 1.85rem;
            font-weight: 700;
            color: var(--text);
            letter-spacing: -0.03em;
            margin-top: 0.2rem;
        }}
        .metric-delta {{
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 0.4rem;
            padding: 2px 8px;
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 3px;
        }}
        .delta-up {{ color: var(--green); background: var(--green-muted); }}
        .delta-down {{ color: var(--red); background: var(--red-muted); }}
        .delta-warn {{ color: var(--amber); background: var(--amber-muted); }}

        /* Chart container wrap */
        .chart-wrap {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.4rem;
            box-shadow: var(--shadow);
            margin-bottom: 1.25rem;
        }}
        .chart-header {{
            margin-bottom: 1rem;
        }}
        .chart-title {{
            font-size: 0.88rem;
            font-weight: 600;
            color: var(--text);
        }}
        .chart-subtitle {{
            font-size: 0.75rem;
            color: var(--text-dim);
            margin-top: 0.1rem;
        }}

        /* Data table custom formatting */
        .table-wrap {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.4rem;
            box-shadow: var(--shadow);
            margin-bottom: 1.25rem;
            overflow-x: auto;
        }}
        .data-table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.82rem;
        }}
        .data-table th {{
            text-align: left;
            padding: 0.75rem 0.9rem;
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 2px solid var(--border);
            background: var(--bg-subtle);
        }}
        .data-table td {{
            padding: 0.75rem 0.9rem;
            color: var(--text);
            border-bottom: 1px solid var(--border-subtle);
            font-family: inherit;
        }}
        .data-table tr:hover td {{
            background-color: var(--bg-subtle);
        }}
        .data-table tr:last-child td {{
            border-bottom: none;
        }}

        /* Status Badges */
        .badge {{
            display: inline-block;
            padding: 2px 9px;
            border-radius: 6px;
            font-size: 0.72rem;
            font-weight: 600;
        }}
        .badge-green {{ color: var(--green); background: var(--green-muted); }}
        .badge-red {{ color: var(--red); background: var(--red-muted); }}
        .badge-amber {{ color: var(--amber); background: var(--amber-muted); }}
        .badge-blue {{ color: var(--accent); background: rgba(37,99,235,0.1); }}

        /* Executive Brand Banner styling */
        .brand-wrap {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        .brand-title {{
            font-size: 1.45rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .brand-subtitle {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.2rem;
        }}
        
        /* Insight section styling */
        .insight-card {{
            background: var(--bg-subtle);
            border-left: 4px solid var(--accent);
            border-radius: 4px;
            padding: 0.9rem 1.2rem;
            margin-bottom: 1rem;
        }}
        .insight-title {{
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text);
        }}
        .insight-desc {{
            font-size: 0.78rem;
            color: var(--text-muted);
            margin-top: 0.3rem;
            line-height: 1.4;
        }}
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
    col_left, col_right = st.columns([5, 1])
    with col_left:
        st.markdown(f"""
        <div class="brand-wrap-inline">
            <div class="brand-title">📊 {title}</div>
            <div class="brand-subtitle">Dashboard Executivo de Inteligência de Vendas e Notas Fiscais</div>
        </div>
        """, unsafe_allow_html=True)
    with col_right:
        theme_label = "☀️ Modo Claro" if is_dark else "🌙 Modo Escuro"
        st.button(theme_label, on_click=toggle_callback, use_container_width=True)
        
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
