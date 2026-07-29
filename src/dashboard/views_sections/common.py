"""Shared plotting and formatting helpers for dashboard view sections."""

from __future__ import annotations


def format_currency(value: float) -> str:
    """Formats numeric values as BRL currency."""
    return f"R$ {value:,.2f}"


def get_plot_layout(is_dark: bool) -> dict:
    """
    Configuração padrão dos gráficos Plotly.
    """

    text_color = "#d4d4d8" if is_dark else "#27272a"
    grid_color = (
        "rgba(255,255,255,0.08)"
        if is_dark
        else "rgba(0,0,0,0.08)"
    )

    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",

        font=dict(
            family="DM Sans, sans-serif",
            color=text_color,
            size=11,
        ),

        legend=dict(
            font=dict(
                color=text_color,
                size=12,
            ),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            orientation="h",
        ),

        margin=dict(
            l=40,
            r=40,
            t=30,
            b=40,
        ),

        xaxis=dict(
            title_font=dict(
                color=text_color,
                size=11,
            ),
            tickfont=dict(
                color=text_color,
                size=10,
            ),
            gridcolor=grid_color,
            zerolinecolor=grid_color,
        ),

        yaxis=dict(
            title_font=dict(
                color=text_color,
                size=11,
            ),
            tickfont=dict(
                color=text_color,
                size=10,
            ),
            gridcolor=grid_color,
            zerolinecolor=grid_color,
        ),
    )