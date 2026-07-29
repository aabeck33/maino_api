"""Domain-oriented dashboard views modules."""

from .customers import render_customers
from .fiscal import render_fiscal
from .geography import render_geography
from .insights import render_insights
from .overview import render_overview
from .products import render_orders, render_products
from .profitability import render_profitability
from .representatives import render_representatives

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
