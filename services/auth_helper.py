"""
Authentication helper functions for Google OAuth and JWT operations
"""
from fastapi import HTTPException, status
from typing import Dict, Any
import jwt
from datetime import datetime, timedelta
import os
import hashlib
import secrets
from google.auth.transport import requests
from google.oauth2 import id_token
import google.auth.exceptions
from database.models import User, SubscriptionType
from config.variable import JWT_SECRET_KEY,GOOGLE_OAUTH_CLIENT_ID

def hash_password(password: str) -> str:
    """Hash a password with salt for secure storage"""
    # Generate a random salt
    salt = secrets.token_hex(32)
    
    # Hash the password with the salt
    password_hash = hashlib.pbkdf2_hmac('sha256', 
                                       password.encode('utf-8'), 
                                       salt.encode('utf-8'), 
                                       100000)  # 100,000 iterations
    
    # Return salt + hash as hex string
    return salt + password_hash.hex()


def verify_password(password: str, stored_password: str) -> bool:
    """Verify a password against a stored hash"""
    # Extract salt (first 64 characters) and hash (remaining)
    salt = stored_password[:64]
    stored_hash = stored_password[64:]
    
    # Hash the provided password with the same salt
    password_hash = hashlib.pbkdf2_hmac('sha256',
                                       password.encode('utf-8'),
                                       salt.encode('utf-8'),
                                       100000)
    
    # Compare hashes
    return password_hash.hex() == stored_hash


async def create_user_with_password(email: str, password: str, name: str) -> Dict[str, Any]:
    """Create a new user with email/password authentication"""
    try:
        # Check if user already exists
        existing_user = await User.find_one(User.email == email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Generate username from email
        username = email.split("@")[0]
        
        # Ensure username is unique
        counter = 1
        original_username = username
        while await User.find_one(User.username == username):
            username = f"{original_username}{counter}"
            counter += 1
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            name=name,
            password_hash=hashed_password,
            subscription_type=SubscriptionType.TRIAL,
            credits_remaining=10,
            subscription_start_date=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_login=datetime.now()
        )
        
        await new_user.insert()
        
        return {
            "id": str(new_user.id),
            "email": new_user.email,
            "username": new_user.username,
            "name": new_user.name,
            "created_at": new_user.created_at,
            "updated_at": new_user.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


async def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticate user with email and password"""
    try:
        # Find user by email
        user = await User.find_one(User.email == email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user has a password (might be Google OAuth only)
        if not hasattr(user, 'password_hash') or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please use Google OAuth to sign in"
            )
        
        # Verify password
        if not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        user.last_login = datetime.now()
        user.updated_at = datetime.now()
        await user.save()
        
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "name": getattr(user, 'name', ''),
            "picture": getattr(user, 'picture', None),
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )


async def verify_google_id_token(id_token_str: str) -> Dict[str, Any]:
    """Verify Google ID token using Google's official library"""
    try:
        # Get Google OAuth client ID from environment
        client_id = GOOGLE_OAUTH_CLIENT_ID
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth client ID not configured"
            )
        
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            id_token_str, 
            requests.Request(), 
            client_id
        )
        
        # Additional checks
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
        
        return idinfo
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {str(e)}"
        )
    except google.auth.exceptions.GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication error: {str(e)}"
        )


async def verify_google_access_token(access_token: str) -> Dict[str, Any]:
    """Verify Google access token and get user info"""
    try:
        # Use Google's tokeninfo endpoint to verify access token
        import requests as req
        
        response = req.get(
            f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}"
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google access token"
            )
        
        token_info = response.json()
        
        # Get user info using the access token
        user_response = req.get(
            f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
        )
        
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to get user info from Google"
            )
        
        user_data = user_response.json()
        return user_data
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying Google access token: {str(e)}"
        )


def generate_jwt_token(user_id: str, email: str) -> tuple[str, str]:
    """Generate JWT access and refresh tokens"""
    secret_key = JWT_SECRET_KEY
    algorithm = "HS256"
    
    # Access token (expires in 1 hour)
    current_time = datetime.now()
    access_payload = {
        "user_id": user_id,
        "email": email,
        "exp": int((current_time + timedelta(hours=1)).timestamp()),
        "iat": int(current_time.timestamp()),
        "type": "access"
    }
    access_token = jwt.encode(access_payload, secret_key, algorithm=algorithm)
    
    # Refresh token (expires in 30 days)
    refresh_payload = {
        "user_id": user_id,
        "email": email,
        "exp": int((current_time + timedelta(days=30)).timestamp()),
        "iat": int(current_time.timestamp()),
        "type": "refresh"
    }
    refresh_token = jwt.encode(refresh_payload, secret_key, algorithm=algorithm)
    
    return access_token, refresh_token


async def create_or_update_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create new user or update existing user in database using Beanie"""
    try:
        # Check if user already exists
        existing_user = await User.find_one(User.email == user_data["email"])
        
        if existing_user:
            # Update existing user
            existing_user.email = user_data["email"]
            existing_user.updated_at = datetime.now()
            existing_user.last_login = datetime.now()
            
            # Add Google-specific fields if they don't exist
            if not hasattr(existing_user, 'google_id'):
                existing_user.google_id = user_data["id"]
            if not hasattr(existing_user, 'name'):
                existing_user.name = user_data.get("name", "")
            if not hasattr(existing_user, 'picture'):
                existing_user.picture = user_data.get("picture")
            if not hasattr(existing_user, 'given_name'):
                existing_user.given_name = user_data.get("given_name")
            if not hasattr(existing_user, 'family_name'):
                existing_user.family_name = user_data.get("family_name")
            
            await existing_user.save()
            
            return {
                "id": str(existing_user.id),
                "email": existing_user.email,
                "username": existing_user.username,
                "name": getattr(existing_user, 'name', ''),
                "picture": getattr(existing_user, 'picture', None),
                "given_name": getattr(existing_user, 'given_name', None),
                "family_name": getattr(existing_user, 'family_name', None),
                "created_at": existing_user.created_at,
                "updated_at": existing_user.updated_at
            }
        else:
            # Create new user
            # Generate username from email if not provided
            username = user_data["email"].split("@")[0]
            
            # Ensure username is unique
            counter = 1
            original_username = username
            while await User.find_one(User.username == username):
                username = f"{original_username}{counter}"
                counter += 1
            
            new_user = User(
                username=username,
                email=user_data["email"],
                subscription_type=SubscriptionType.TRIAL,
                credits_remaining=10,
                subscription_start_date=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Add Google-specific fields
            new_user.google_id = user_data["id"]
            new_user.name = user_data.get("name", "")
            new_user.picture = user_data.get("picture")
            new_user.given_name = user_data.get("given_name")
            new_user.family_name = user_data.get("family_name")
            new_user.last_login = datetime.now()
            
            await new_user.insert()
            
            return {
                "id": str(new_user.id),
                "email": new_user.email,
                "username": new_user.username,
                "name": new_user.name,
                "picture": new_user.picture,
                "given_name": new_user.given_name,
                "family_name": new_user.family_name,
                "created_at": new_user.created_at,
                "updated_at": new_user.updated_at
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )