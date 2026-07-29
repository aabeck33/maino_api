"""Backward-compatible exports for dashboard view renderers.

This module re-exports the final domain modules from dashboard.views_sections.
"""

from __future__ import annotations

from dashboard.views_sections import (
    render_customers,
    render_fiscal,
    render_geography,
    render_insights,
    render_orders,
    render_overview,
    render_products,
    render_profitability,
    render_representatives,
)

__all__ = [
    "render_overview",
    "render_profitability",
    "render_representatives",
    "render_customers",
    "render_products",
    "render_orders",
    "render_geography",
    "render_fiscal",
    "render_insights",
]
