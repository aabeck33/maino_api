"""Centralized KPI modules by business domain."""

from .sales_kpis import (
    build_abc_analysis,
    build_abc_pareto_analysis,
    calculate_core_sales_kpis,
    calculate_order_stats,
    calculate_fiscal_distribution,
)
from .customer_kpis import summarize_customers
from .representative_kpis import (
    build_representative_monthly_evolution,
    calculate_representative_performance,
    summarize_representative_sales,
)
from .geography_kpis import (
    calculate_clients_by_state,
    calculate_revenue_by_city,
    calculate_state_geo_coordinates,
    calculate_state_revenue,
    calculate_state_ticket_average,
    top_cities_by_customers,
    top_cities_by_revenue,
)
from .profitability_kpis import (
    build_profitability_dataset,
    calculate_financial_kpis,
    summarize_profitability_by_customer,
    summarize_profitability_by_product,
    summarize_profitability_by_representative,
    summarize_monthly_profitability,
)

__all__ = [
    "build_abc_analysis",
    "build_abc_pareto_analysis",
    "calculate_core_sales_kpis",
    "calculate_order_stats",
    "calculate_fiscal_distribution",
    "summarize_customers",
    "build_representative_monthly_evolution",
    "calculate_representative_performance",
    "summarize_representative_sales",
    "calculate_clients_by_state",
    "calculate_revenue_by_city",
    "calculate_state_geo_coordinates",
    "calculate_state_revenue",
    "calculate_state_ticket_average",
    "top_cities_by_customers",
    "top_cities_by_revenue",
    "build_profitability_dataset",
    "calculate_financial_kpis",
    "summarize_profitability_by_customer",
    "summarize_profitability_by_product",
    "summarize_profitability_by_representative",
    "summarize_monthly_profitability",
]
