from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import Base, engine
from app.middleware.rate_limit import limiter
from app.routers import auth_router

# ============================================
# AUTO-MIGRATION
# ============================================

def auto_migrate():
    """Check and add missing columns on startup"""
    inspector = inspect(engine)
    Base.metadata.create_all(bind=engine)
    
    if 'users' in inspector.get_table_names():
        existing_columns = {col['name'] for col in inspector.get_columns('users')}
        
        required_columns = {
            'verification_token': 'VARCHAR(255)',
            'verification_token_expires': 'TIMESTAMP WITH TIME ZONE',
            'verification_sent_at': 'TIMESTAMP WITH TIME ZONE',
            'reset_token': 'VARCHAR(255)',
            'reset_token_expires': 'TIMESTAMP WITH TIME ZONE',
            'reset_sent_at': 'TIMESTAMP WITH TIME ZONE',
            'reset_used_at': 'TIMESTAMP WITH TIME ZONE',
        }
        
        with engine.begin() as conn:
            for col_name, col_type in required_columns.items():
                if col_name not in existing_columns:
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                        print(f"✅ Added column: {col_name}")
                    except Exception as e:
                        print(f"⚠️  Column {col_name}: {e}")

# ============================================
# LIFESPAN
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n🚀 Starting NexroCampus Backend...")
    auto_migrate()
    print("✅ Database ready")
    print("🛡️ Rate limiting active\n")
    yield
    print("\n👋 Shutting down...")

# ============================================
# CREATE APP
# ============================================

app = FastAPI(
    title=settings.APP_NAME,
    description="Study App Backend API",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# ============================================
# RATE LIMITING
# ============================================

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ============================================
# CORS
# ============================================

origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ROUTES
# ============================================

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

@app.get("/")
async def root():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "rate_limit": "active"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)