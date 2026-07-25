from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    full_name = Column(String(100), nullable=False)
    
    # Profile fields
    avatar_url = Column(String, nullable=True)
    university = Column(String(150), nullable=True)
    major = Column(String(100), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    
    # Plan
    plan_type = Column(String(20), default='free')
    
    # ============================================
    # EMAIL VERIFICATION
    # ============================================
    verification_token = Column(String(255), nullable=True, unique=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    verification_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # ============================================
    # PASSWORD RESET (NEW)
    # ============================================
    reset_token = Column(String(255), nullable=True, unique=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    reset_sent_at = Column(DateTime(timezone=True), nullable=True)
    reset_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # ============================================
    # TIMESTAMPS
    # ============================================
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User {self.email}>"