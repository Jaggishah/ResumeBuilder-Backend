from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from datetime import datetime
from typing import Optional, Dict, Any
from config.variable import JWT_SECRET_KEY

security = HTTPBearer()

def get_jwt_secret_key() -> str:
    """Get JWT secret key from environment"""
    return JWT_SECRET_KEY

async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify JWT token and return user payload
    Use this as a dependency in protected routes
    """
    try:
        # Decode the token
        payload = jwt.decode(
            credentials.credentials,
            get_jwt_secret_key(),
            algorithms=["HS256"]
        )
        
        # Check if token is access token
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # JWT decode already handles expiration checking
        return payload
        
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token_payload: Dict[str, Any] = Depends(verify_jwt_token)) -> Dict[str, Any]:
    """
    Get current user from JWT token
    Use this as a dependency to get user info in protected routes
    """
    return {
        "user_id": token_payload.get("user_id"),
        "email": token_payload.get("email"),
        "exp": token_payload.get("exp"),
        "iat": token_payload.get("iat")
    }

def create_jwt_dependency(required: bool = True):
    """
    Create a JWT dependency that can be required or optional
    
    Usage:
    @app.get("/protected")
    async def protected_route(user = Depends(create_jwt_dependency(required=True))):
        pass
    
    @app.get("/optional-auth")
    async def optional_auth_route(user = Depends(create_jwt_dependency(required=False))):
        pass
    """
    async def jwt_dependency(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=required))):
        if not credentials:
            if required:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None
        
        return await verify_jwt_token(credentials)
    
    return jwt_dependency