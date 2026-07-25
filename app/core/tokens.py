import secrets
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.core.config import settings

# ============================================
# EMAIL VERIFICATION TOKEN
# ============================================

def create_verification_token(user_id: int) -> str:
    """Create a unique email verification token (24 hour expiry)"""
    payload = {
        "user_id": user_id,
        "type": "email_verification",
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

def verify_verification_token(token: str):
    """Verify email verification token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "email_verification":
            return None
        
        return payload
    except JWTError:
        return None


# ============================================
# PASSWORD RESET TOKEN (NEW)
# ============================================

def create_reset_token(user_id: int) -> str:
    """Create a password reset token (1 hour expiry)"""
    payload = {
        "user_id": user_id,
        "type": "password_reset",
        "exp": datetime.utcnow() + timedelta(hours=1),  # 1 hour only
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(
        payload,
        settings.JWT_REFRESH_SECRET,  # Use different secret!
        algorithm=settings.JWT_ALGORITHM
    )

def verify_reset_token(token: str):
    """Verify password reset token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_REFRESH_SECRET,  # Must match!
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "password_reset":
            return None
        
        return payload
    except JWTError:
        return None


# ============================================
# HELPER
# ============================================

def generate_random_token(length: int = 32) -> str:
    """Generate a random secure token"""
    return secrets.token_urlsafe(length)