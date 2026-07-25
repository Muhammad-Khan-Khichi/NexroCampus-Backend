from app.core.database import get_db

# Re-export so it can be imported from app.dependencies
__all__ = ["get_db"]