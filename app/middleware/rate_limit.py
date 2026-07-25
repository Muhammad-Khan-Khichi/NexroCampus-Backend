from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# ============================================
# RATE LIMITER
# ============================================

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",  # In-memory storage
    default_limits=["100 per hour"],
    headers_enabled=True,  # Add X-RateLimit headers
)

# Rate limit messages
RATE_LIMIT_MESSAGES = {
    "login": "Too many login attempts. Please try again in 15 minutes.",
    "signup": "Too many signup attempts. Please try again in an hour.",
    "forgot_password": "Too many password reset requests. Please try again later.",
    "verify_email": "Too many verification attempts.",
    "default": "Rate limit exceeded. Please slow down.",
}