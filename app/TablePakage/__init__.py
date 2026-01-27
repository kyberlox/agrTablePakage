"""
Your FastAPI Application
"""

from .model.database import Base
from .router.products import router as products_router
from .router.parameters  import router as parameters_router
from .router.tables import router as tables_router
from .router.formulas import router as formulas_router

__all__ = ["products_router"]
__version__ = "1.0.0"