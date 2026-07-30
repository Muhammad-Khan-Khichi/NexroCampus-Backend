from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
from typing import Optional

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    SignupRequest, LoginRequest, ResendVerificationRequest,
    GoogleLoginRequest, GitHubLoginRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
    OAuthAuthURLResponse,
    SignupResponse, LoginResponse, RefreshResponse,
    UserResponse, MessageResponse
)
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    verify_access_token, verify_refresh_token
)
from app.core.config import settings
from app.core.tokens import (
    create_verification_token, verify_verification_token,
    create_reset_token, verify_reset_token
)
from app.services.email import (
    send_verification_email,
    send_password_reset_email,
    send_password_changed_email
)
from app.services.oauth import google_oauth, github_oauth

# ============================================
# ROUTER & RATE LIMITER
# ============================================

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ============================================
# COOKIE HELPERS
# ============================================

REFRESH_TOKEN_COOKIE = "refresh_token"

def set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

def clear_refresh_cookie(response: Response):
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/")

def get_refresh_token_from_cookie(request: Request) -> str:
    token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token"
        )
    return token


# ============================================
# SIGNUP
# ============================================

@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10 per hour")
async def signup(
    request: Request,
    signup_data: SignupRequest,
    db: Session = Depends(get_db)
):
    """Register a new user and send verification email"""
    
    existing_user = db.query(User).filter(User.email == signup_data.email).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    new_user = User(
        email=signup_data.email,
        password_hash=hash_password(signup_data.password),
        full_name=signup_data.full_name,
        email_verified=False,
        plan_type='free',
        is_active=True,
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    verification_token = create_verification_token(new_user.id)
    
    new_user.verification_token = verification_token
    new_user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    new_user.verification_sent_at = datetime.utcnow()
    db.commit()
    
    verification_sent = await send_verification_email(
        email=new_user.email,
        full_name=new_user.full_name,
        token=verification_token
    )
    
    return SignupResponse(
        message=f"Account created! Please check your email to verify your account.",
        email=new_user.email,
        verification_sent=verification_sent
    )


# ============================================
# LOGIN
# ============================================

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5 per 15 minutes")
async def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Login with email and password"""
    
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.password_hash or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in"
        )
    
    access_token = create_access_token({"sub": user.email, "user_id": user.id})
    refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
    
    set_refresh_cookie(response, refresh_token)
    
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            email_verified=user.email_verified,
            plan_type=user.plan_type,
            created_at=user.created_at
        ),
        is_new_user=False
    )


# ============================================
# FORGOT PASSWORD
# ============================================

@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3 per hour")
async def forgot_password(
    request: Request,
    request_data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """Initiate password reset"""
    
    user = db.query(User).filter(User.email == request_data.email).first()
    
    if user and user.password_hash:
        reset_token = create_reset_token(user.id)
        
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        user.reset_sent_at = datetime.utcnow()
        user.reset_used_at = None
        db.commit()
        
        await send_password_reset_email(
            email=user.email,
            full_name=user.full_name,
            token=reset_token
        )
    
    return MessageResponse(
        message="If an account exists with this email, a password reset link has been sent.",
        success=True
    )


# ============================================
# RESET PASSWORD
# ============================================

@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5 per hour")
async def reset_password(
    request: Request,
    reset_data: ResetPasswordRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Reset password using token from email"""
    
    payload = verify_reset_token(reset_data.token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.reset_token != reset_data.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used or is invalid"
        )
    
    if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link has expired. Please request a new one."
        )
    
    user.password_hash = hash_password(reset_data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.reset_used_at = datetime.utcnow()
    
    db.commit()
    
    clear_refresh_cookie(response)
    
    await send_password_changed_email(
        email=user.email,
        full_name=user.full_name
    )
    
    return MessageResponse(
        message="✅ Password reset successfully! You can now log in with your new password.",
        success=True
    )


# ============================================
# VERIFY RESET TOKEN
# ============================================

@router.get("/verify-reset-token/{token}", response_model=MessageResponse)
@limiter.limit("20 per hour")
async def verify_reset_token_endpoint(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """Check if reset token is valid"""
    
    payload = verify_reset_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.reset_token != token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used"
        )
    
    if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset link has expired"
        )
    
    return MessageResponse(
        message="Reset link is valid",
        success=True
    )


# ============================================
# GOOGLE OAUTH - LOGIN URL
# ============================================

@router.get("/google/login", response_model=OAuthAuthURLResponse)
@limiter.limit("20 per hour")
async def google_login_redirect(
    request: Request,
    redirect_uri: Optional[str] = Query(None)
):
    """Get Google OAuth authorization URL"""
    
    try:
        if not redirect_uri:
            redirect_uri = f"{settings.FRONTEND_URL}/auth/google/callback"
        
        state = secrets.token_urlsafe(32)
        auth_url = google_oauth.get_authorize_url(
            redirect_uri=redirect_uri,
            state=state
        )
        
        return OAuthAuthURLResponse(
            auth_url=auth_url,
            state=state,
            provider="google"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


# ============================================
# GOOGLE OAUTH - GET CALLBACK (called by Google)
# ============================================

@router.get("/google/callback")
async def google_callback_get(
    request: Request,
    code: str,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback (called by Google via GET)"""
    
    try:
        print(f"🔵 Google callback received with code: {code[:20]}...")
        
        user_info = await google_oauth.get_user_info(
            code=code,
            redirect_uri=f"{settings.FRONTEND_URL}/auth/google/callback"
        )
        
        email = user_info.get("email")
        full_name = user_info.get("name", "")
        avatar_url = user_info.get("picture")
        email_verified = user_info.get("email_verified", False)
        
        if not email:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=email_not_provided"
            )
        
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            user = User(
                email=email,
                password_hash=None,
                full_name=full_name or email.split("@")[0],
                avatar_url=avatar_url,
                email_verified=email_verified,
                plan_type='free',
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            if not user.avatar_url and avatar_url:
                user.avatar_url = avatar_url
            if not user.email_verified and email_verified:
                user.email_verified = email_verified
            db.commit()
        
        access_token = create_access_token({"sub": user.email, "user_id": user.id})
        refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}&provider=google"
        )
    
    except Exception as e:
        print(f"❌ Google OAuth error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=oauth_failed"
        )


# ============================================
# GOOGLE OAUTH - POST CALLBACK (called by frontend)
# ============================================

@router.post("/google/callback", response_model=LoginResponse)
@limiter.limit("20 per hour")
async def google_callback(
    request: Request,
    google_data: GoogleLoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback from frontend POST"""
    
    try:
        user_info = await google_oauth.get_user_info(
            code=google_data.code,
            redirect_uri=google_data.redirect_uri
        )
        
        email = user_info.get("email")
        full_name = user_info.get("name", "")
        avatar_url = user_info.get("picture")
        email_verified = user_info.get("email_verified", False)
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )
        
        user = db.query(User).filter(User.email == email).first()
        is_new_user = False
        
        if not user:
            user = User(
                email=email,
                password_hash=None,
                full_name=full_name or email.split("@")[0],
                avatar_url=avatar_url,
                email_verified=email_verified,
                plan_type='free',
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            is_new_user = True
        else:
            if not user.avatar_url and avatar_url:
                user.avatar_url = avatar_url
            if not user.email_verified and email_verified:
                user.email_verified = email_verified
            db.commit()
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        access_token = create_access_token({"sub": user.email, "user_id": user.id})
        refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
        
        set_refresh_cookie(response, refresh_token)
        
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                email_verified=user.email_verified,
                plan_type=user.plan_type,
                created_at=user.created_at
            ),
            is_new_user=is_new_user
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth failed: {str(e)}"
        )


# ============================================
# GITHUB OAUTH - LOGIN URL
# ============================================

@router.get("/github/login", response_model=OAuthAuthURLResponse)
@limiter.limit("20 per hour")
async def github_login_redirect(
    request: Request,
    redirect_uri: Optional[str] = Query(None)
):
    """Get GitHub OAuth authorization URL"""
    
    try:
        if not redirect_uri:
            redirect_uri = "http://localhost:8000/api/auth/github/callback"
        
        state = secrets.token_urlsafe(32)
        auth_url = github_oauth.get_authorize_url(
            redirect_uri=redirect_uri,
            state=state
        )
        
        return OAuthAuthURLResponse(
            auth_url=auth_url,
            state=state,
            provider="github"
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


# ============================================
# GITHUB OAUTH - GET CALLBACK (called by GitHub)
# ============================================

@router.get("/github/callback")
async def github_callback_get(
    request: Request,
    code: str,
    db: Session = Depends(get_db)
):
    """Handle GitHub OAuth callback (called by GitHub via GET)"""
    
    try:
        print(f"🔵 GitHub callback received with code: {code[:20]}...")
        print("=" * 50)
        print(f"🔵 GitHub callback received!")
        print(f"📌 Code: {code[:20]}...")
        print(f"📌 FRONTEND_URL: {settings.FRONTEND_URL}")
        print("=" * 50)
        
        user_info = await github_oauth.get_user_info(
            code=code,
            redirect_uri=f"{settings.FRONTEND_URL}/auth/github/callback"
        )
        
        email = user_info.get("email")
        full_name = user_info.get("name", "")
        avatar_url = user_info.get("picture")
        
        if not email:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/login?error=email_not_provided"
            )
        
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            user = User(
                email=email,
                password_hash=None,
                full_name=full_name or email.split("@")[0],
                avatar_url=avatar_url,
                email_verified=True,
                plan_type='free',
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        access_token = create_access_token({"sub": user.email, "user_id": user.id})
        refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
        
        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}&provider=github"
        )
    
    except Exception as e:
        print(f"❌ GitHub OAuth error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/login?error=oauth_failed"
        )


# ============================================
# GITHUB OAUTH - POST CALLBACK (called by frontend)
# ============================================

@router.post("/github/callback", response_model=LoginResponse)
@limiter.limit("20 per hour")
async def github_callback(
    request: Request,
    github_data: GitHubLoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Handle GitHub OAuth callback from frontend POST"""
    
    try:
        user_info = await github_oauth.get_user_info(
            code=github_data.code,
            redirect_uri=github_data.redirect_uri
        )
        
        email = user_info.get("email")
        full_name = user_info.get("name", "")
        avatar_url = user_info.get("picture")
        email_verified = user_info.get("email_verified", False)
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by GitHub"
            )
        
        user = db.query(User).filter(User.email == email).first()
        is_new_user = False
        
        if not user:
            user = User(
                email=email,
                password_hash=None,
                full_name=full_name or email.split("@")[0],
                avatar_url=avatar_url,
                email_verified=email_verified,
                plan_type='free',
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            is_new_user = True
        else:
            if not user.avatar_url and avatar_url:
                user.avatar_url = avatar_url
            if not user.email_verified and email_verified:
                user.email_verified = email_verified
            db.commit()
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        access_token = create_access_token({"sub": user.email, "user_id": user.id})
        refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
        
        set_refresh_cookie(response, refresh_token)
        
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                email_verified=user.email_verified,
                plan_type=user.plan_type,
                created_at=user.created_at
            ),
            is_new_user=is_new_user
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub OAuth failed: {str(e)}"
        )


# ============================================
# VERIFY EMAIL
# ============================================

@router.post("/verify-email", response_model=MessageResponse)
@limiter.limit("10 per hour")
async def verify_email(
    request: Request,
    token: str,
    db: Session = Depends(get_db)
):
    """Verify email address using token"""
    
    payload = verify_verification_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.email_verified:
        return MessageResponse(
            message="Email already verified!",
            success=True
        )
    
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    
    return MessageResponse(
        message="✅ Email verified successfully!",
        success=True
    )


# ============================================
# RESEND VERIFICATION
# ============================================

@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("3 per hour")
async def resend_verification(
    request: Request,
    request_data: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    """Resend verification email"""
    
    user = db.query(User).filter(User.email == request_data.email).first()
    
    if not user:
        return MessageResponse(
            message="If the email exists, a verification link has been sent."
        )
    
    if user.email_verified:
        return MessageResponse(
            message="Email is already verified."
        )
    
    verification_token = create_verification_token(user.id)
    
    user.verification_token = verification_token
    user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
    user.verification_sent_at = datetime.utcnow()
    db.commit()
    
    await send_verification_email(
        email=user.email,
        full_name=user.full_name,
        token=verification_token
    )
    
    return MessageResponse(
        message="Verification email sent!"
    )


# ============================================
# REFRESH TOKEN
# ============================================

@router.post("/refresh", response_model=RefreshResponse)
@limiter.limit("30 per hour")
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Get new access token using refresh token from cookie"""
    
    refresh_token_value = get_refresh_token_from_cookie(request)
    
    payload = verify_refresh_token(refresh_token_value)
    
    if not payload:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    new_access_token = create_access_token({"sub": user.email, "user_id": user.id})
    new_refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
    set_refresh_cookie(response, new_refresh_token)
    
    return RefreshResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ============================================
# LOGOUT
# ============================================

@router.post("/logout", response_model=MessageResponse)
@limiter.limit("100 per hour")
async def logout(
    request: Request,
    response: Response
):
    """Logout and clear refresh token"""
    
    clear_refresh_cookie(response)
    return MessageResponse(message="Logged out successfully")


# ============================================
# ME
# ============================================

@router.get("/me", response_model=UserResponse)
@limiter.limit("100 per hour")
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get current logged-in user info"""
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        email_verified=current_user.email_verified,
        plan_type=current_user.plan_type,
        created_at=current_user.created_at
    )