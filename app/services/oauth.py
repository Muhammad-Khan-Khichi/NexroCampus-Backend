import httpx
from typing import Optional, Dict
from authlib.integrations.httpx_client import AsyncOAuth2Client
from app.core.config import settings

# ============================================
# GOOGLE OAUTH CONFIG
# ============================================

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_EMAILS_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# ============================================
# GITHUB OAUTH CONFIG
# ============================================

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


class GoogleOAuth:
    """Google OAuth handler"""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
    
    def get_authorize_url(self, redirect_uri: str, state: str = None) -> str:
        """Generate Google OAuth authorization URL"""
        
        if not self.client_id:
            raise ValueError("GOOGLE_CLIENT_ID not configured")
        
        client = AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        
        url, _ = client.create_authorization_url(
            GOOGLE_AUTHORIZE_URL,
            redirect_uri=redirect_uri,
            scope=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
            state=state,
        )
        
        return url
    
    async def get_user_info(self, code: str, redirect_uri: str) -> Dict:
        """Exchange code for user info"""
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth not configured")
        
        async with httpx.AsyncClient() as client:
            # Step 1: Exchange code for access token
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"}
            )
            
            if token_response.status_code != 200:
                raise Exception(f"Failed to get token: {token_response.text}")
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise Exception("No access token in response")
            
            # Step 2: Get user info
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                raise Exception(f"Failed to get user info: {userinfo_response.text}")
            
            return userinfo_response.json()


class GitHubOAuth:
    """GitHub OAuth handler"""
    
    def __init__(self):
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
    
    def get_authorize_url(self, redirect_uri: str, state: str = None) -> str:
        """Generate GitHub OAuth authorization URL"""
        
        if not self.client_id:
            raise ValueError("GITHUB_CLIENT_ID not configured")
        
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "user:email",  # Request access to email
            "allow_signup": "true",
        }
        
        if state:
            params["state"] = state
        
        # Build URL
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GITHUB_AUTHORIZE_URL}?{query_string}"
    
    async def get_user_info(self, code: str, redirect_uri: str) -> Dict:
        """Exchange code for user info"""
        
        if not self.client_id or not self.client_secret:
            raise ValueError("GitHub OAuth not configured")
        
        async with httpx.AsyncClient() as client:
            # Step 1: Exchange code for access token
            token_response = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={
                    "Accept": "application/json",
                }
            )
            
            if token_response.status_code != 200:
                raise Exception(f"Failed to get token: {token_response.text}")
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise Exception("No access token in response")
            
            # Step 2: Get user info
            user_response = await client.get(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                }
            )
            
            if user_response.status_code != 200:
                raise Exception(f"Failed to get user info: {user_response.text}")
            
            user_data = user_response.json()
            
            # Step 3: Get primary email (might be private)
            email = user_data.get("email")
            
            if not email:
                # Fetch from emails endpoint
                emails_response = await client.get(
                    GITHUB_EMAILS_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github+json",
                    }
                )
                
                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    # Find primary email
                    for email_obj in emails:
                        if email_obj.get("primary") and email_obj.get("verified"):
                            email = email_obj.get("email")
                            break
            
            # Build standardized user data
            return {
                "sub": str(user_data.get("id")),
                "email": email,
                "email_verified": True,  # GitHub emails are pre-verified
                "name": user_data.get("name") or user_data.get("login"),
                "picture": user_data.get("avatar_url"),
                "username": user_data.get("login"),
            }


# Singleton instances
google_oauth = GoogleOAuth()
github_oauth = GitHubOAuth()