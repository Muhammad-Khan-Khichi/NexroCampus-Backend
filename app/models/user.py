# app/models/user.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
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
    # 🆕 STORAGE TRACKING (SaaS)
    # ============================================
    storage_used_bytes = Column(BigInteger, default=0, nullable=False)
    storage_limit_bytes = Column(BigInteger, default=52428800, nullable=False)  # 50MB default for free
    lectures_count = Column(Integer, default=0, nullable=False)
    
    # ============================================
    # EMAIL VERIFICATION
    # ============================================
    verification_token = Column(String(255), nullable=True, unique=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)
    verification_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # ============================================
    # PASSWORD RESET
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
    
    # ============================================
    # 🆕 HELPER METHODS
    # ============================================
    def get_storage_used_mb(self) -> float:
        """Get storage used in MB"""
        return self.storage_used_bytes / (1024 * 1024)
    
    def get_storage_limit_mb(self) -> float:
        """Get storage limit in MB"""
        return self.storage_limit_bytes / (1024 * 1024)
    
    def get_storage_percentage(self) -> float:
        """Get storage usage percentage"""
        if self.storage_limit_bytes == 0:
            return 0
        return (self.storage_used_bytes / self.storage_limit_bytes) * 100
    
    def has_storage_available(self, needed_bytes: int) -> bool:
        """Check if user has enough storage"""
        return (self.storage_used_bytes + needed_bytes) <= self.storage_limit_bytes
    
    def get_remaining_storage(self) -> int:
        """Get remaining storage in bytes"""
        return max(0, self.storage_limit_bytes - self.storage_used_bytes)