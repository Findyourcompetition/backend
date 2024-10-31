# app/services/token_service.py
import jwt
from datetime import datetime, timedelta
from ..database import redis_async 
from ..config import settings
import logging

logger = logging.getLogger(__name__)

async def generate_reset_token(email: str) -> str:
    """Generate a secure reset token."""
    try:
        payload = {
            "email": email,
            "exp": datetime.utcnow() + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
        }
        
        # Generate JWT token
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        # Store token in Redis with expiration
        redis_key = f"reset_token:{token}"
        try:
            await redis_async.setex(
                redis_key,
                settings.RESET_TOKEN_EXPIRE_MINUTES * 60,
                email
            )
        except Exception as redis_error:
            logger.error(f"Redis error: {redis_error}")
            raise Exception("Error storing reset token")
        
        return token
        
    except Exception as e:
        logger.error(f"Token generation error: {str(e)}")
        raise

async def verify_reset_token(token: str) -> str:
    """Verify and decode the reset token."""
    try:
        # Decode and verify the token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Check if token exists in Redis
        redis_key = f"reset_token:{token}"
        stored_email = await redis_async.get(redis_key)
        
        if not stored_email:
            raise Exception("Invalid or expired reset token")
            
        return payload["email"]
        
    except jwt.ExpiredSignatureError:
        raise Exception("Reset token has expired")
    except jwt.JWTError:
        raise Exception("Invalid reset token")
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise
