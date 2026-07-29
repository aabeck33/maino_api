"""Repository layer for data access and normalization."""

from .base import BaseRepository
from .customer_repository import CustomerRepository
from .product_repository import ProductRepository
from .sales_repository import SalesRepository

__all__ = [
    "BaseRepository",
    "CustomerRepository",
    "ProductRepository",
    "SalesRepository",
]
