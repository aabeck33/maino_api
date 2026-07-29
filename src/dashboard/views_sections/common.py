"""Shared plotting and formatting helpers for dashboard view sections."""

from __future__ import annotations


def format_currency(value: float) -> str:
    """Formats numeric values as BRL currency."""
    return f"R$ {value:,.2f}"


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