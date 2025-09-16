"""
Repository layer for database access
Provides CRUD operations for all databases
"""

from .hr_repository import HRRepository
from .sales_repository import SalesRepository
from .vector_repository import VectorRepository

__all__ = [
    "HRRepository",
    "SalesRepository",
    "VectorRepository"
]