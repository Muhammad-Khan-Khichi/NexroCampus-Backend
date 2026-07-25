from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# ============================================
# Neon requires SSL — Handle both local & remote
# ============================================

def get_engine_url():
    """Add SSL params if not present (for Neon)"""
    db_url = settings.DATABASE_URL
    
    # If no sslmode in URL, add it (Neon requirement)
    if "sslmode" not in db_url and "neon.tech" in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"
    
    return db_url

# Create database engine
engine = create_engine(
    get_engine_url(),
    echo=settings.DEBUG,
    pool_pre_ping=True,    # Test connection before using
    pool_recycle=300,      # Recycle connections every 5 min
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()