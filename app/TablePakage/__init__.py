"""
Your FastAPI Application
"""

from .router.products import router as products_router

__all__ = ["products_router"]
__version__ = "1.0.0"