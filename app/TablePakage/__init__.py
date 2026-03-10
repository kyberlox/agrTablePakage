from .model.database import Base
from .router.products import router as products_router
from .router.parameters  import router as parameters_router
from .router.tables import router as tables_router

from .model import *
from .router import *

__all__ = [
    "Base", 
    "products_router", 
    "parameters_router", 
    "tables_router", 
    "router",
    'model'
]
__version__ = "1.0.0"