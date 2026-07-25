from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

# ============================================
# REQUEST SCHEMAS
# ============================================

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('full_name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class GoogleLoginRequest(BaseModel):
    code: str
    redirect_uri: str

class GitHubLoginRequest(BaseModel):
    code: str
    redirect_uri: str

class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset"""
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    """Request to reset password with token"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


# ============================================
# RESPONSE SCHEMAS
# ============================================

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    email_verified: bool
    plan_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class SignupResponse(BaseModel):
    message: str
    email: str
    verification_sent: bool

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    is_new_user: Optional[bool] = False

class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class MessageResponse(BaseModel):
    message: str
    success: bool = True

class OAuthAuthURLResponse(BaseModel):
    auth_url: str
    state: str
    provider: str