from .products import router as products_router
from .parameters  import router as parameters_router
from .tables import router as tables_router

__all__ = [
    "products_router",
    "parameters_router",
    "tables_router"
]
__version__ = "1.0.0"