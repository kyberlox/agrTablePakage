from .model import database

from ..TablePakage.router.products import router as products_router
from ..TablePakage.router.parameters  import router as parameters_router
from ..TablePakage.router.tables import router as tables_router



__all__ = ["database", "products_router", "parameters_router", "tables_router"]
__version__ = "1.0.0"