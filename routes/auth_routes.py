from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import jwt
import os
from middleware.auth import get_current_user
from database.models import User
from services.auth_helper import (
    verify_google_id_token,
    verify_google_access_token,
    generate_jwt_token,
    create_or_update_user,
    create_user_with_password,
    authenticate_user
)
from services.credit_manager import CreditManager
from config.variable import JWT_SECRET_KEY

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Helper function to get user data with credits
async def get_user_data_with_credits(user: User) -> Dict[str, Any]:
    """Get user data including credit information"""
    credit_info = CreditManager.get_subscription_info(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "name": getattr(user, 'name', ''),
        "picture": getattr(user, 'picture', None),
        "given_name": getattr(user, 'given_name', None),
        "family_name": getattr(user, 'family_name', None),
        "resume_count": user.resume_count,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login": getattr(user, 'last_login', None),
        "subscription": {
            "type": credit_info["subscription_type"],
            "credits_remaining": credit_info["credits_remaining"],
            "credits_used": credit_info["credits_used"],
            "is_unlimited": credit_info["is_unlimited"],
            "start_date": credit_info["subscription_start_date"],
            "end_date": credit_info["subscription_end_date"]
        }
    }

# Pydantic models
class GoogleOAuthRequest(BaseModel):
    access_token: str
    id_token: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: Dict[str, Any]
    expires_in: int

class GoogleUserInfo(BaseModel):
    id: str
    email: EmailStr
    name: str
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None

# Routes
@router.post("/google", response_model=AuthResponse)
async def google_oauth(request: GoogleOAuthRequest):
    """
    Authenticate user with Google OAuth
    
    - **access_token**: Google OAuth access token
    - **id_token**: Optional Google ID token for additional verification
    """
    try:
        user_data = None
        
        # If ID token is provided, verify it (preferred method)
        if request.id_token:
            id_token_data = await verify_google_id_token(request.id_token)
            user_data = {
                "id": id_token_data["sub"],
                "email": id_token_data["email"],
                "name": id_token_data.get("name", ""),
                "picture": id_token_data.get("picture"),
                "given_name": id_token_data.get("given_name"),
                "family_name": id_token_data.get("family_name")
            }
        
        # If only access token is provided, verify it
        elif request.access_token:
            user_data = await verify_google_access_token(request.access_token)
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either access_token or id_token must be provided"
            )
        
        # Create or update user in database
        user_record = await create_or_update_user(user_data)
        
        # Get user from database to include credit info
        user = await User.get(user_record["id"])
        user_data_with_credits = await get_user_data_with_credits(user)
        
        # Generate JWT tokens
        access_token, refresh_token = generate_jwt_token(
            user_record["id"], 
            user_record["email"]
        )
        
        # Prepare response
        response = AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_data_with_credits,
            expires_in=3600  # 1 hour in seconds
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate user with email and password
    
    - **email**: User's email address
    - **password**: User's password
    """
    try:
        # Authenticate user
        user_data = await authenticate_user(request.email, request.password)
        
        # Get user from database to include credit info
        user = await User.get(user_data["id"])
        user_data_with_credits = await get_user_data_with_credits(user)
        
        # Generate JWT tokens
        access_token, refresh_token = generate_jwt_token(
            user_data["id"],
            user_data["email"]
        )
        
        # Prepare response
        response = AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_data_with_credits,
            expires_in=3600  # 1 hour in seconds
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    Register a new user with email and password
    
    - **email**: User's email address
    - **password**: User's password
    - **name**: User's full name
    """
    try:
        # Validate password strength (basic validation)
        if len(request.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Create new user
        user_data = await create_user_with_password(
            request.email,
            request.password,
            request.name
        )
        
        # Get user from database to include credit info
        user = await User.get(user_data["id"])
        user_data_with_credits = await get_user_data_with_credits(user)
        
        # Generate JWT tokens
        access_token, refresh_token = generate_jwt_token(
            user_data["id"],
            user_data["email"]
        )
        
        # Prepare response
        response = AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_data_with_credits,
            expires_in=3600  # 1 hour in seconds
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.get("/profile")
async def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current user profile information from JWT token
    Requires Authorization header with Bearer token
    """
    try:
        user = await User.get(current_user["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get user data with credit information
        user_data_with_credits = await get_user_data_with_credits(user)
        
        return user_data_with_credits
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token"""
    try:
        secret_key = JWT_SECRET_KEY
        
        # Decode refresh token
        payload = jwt.decode(refresh_token, secret_key, algorithms=["HS256"])
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Generate new access token
        access_token, _ = generate_jwt_token(
            payload["user_id"],
            payload["email"]
        )
        
        return {
            "access_token": access_token,
            "expires_in": 3600
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/me")
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current authenticated user info"""
    try:
        user = await User.get(current_user["user_id"])
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "name": getattr(user, 'name', ''),
                "picture": getattr(user, 'picture', None),
                "given_name": getattr(user, 'given_name', None),
                "family_name": getattr(user, 'family_name', None),
                "resume_count": user.resume_count,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user: {str(e)}"
        )

@router.post("/logout")
async def logout():
    """Logout user (in a stateless JWT system, this is mainly client-side)"""
    return {"message": "Logged out successfully"}