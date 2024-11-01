# app/services/token_service.py
import logging
from ..database import redis_async 
from ..config import settings

logger = logging.getLogger(__name__)

async def generate_reset_token(email: str) -> str:
    """Generate a 6-character OTP code for password reset."""
    try:
        import random
        import string
        
        # Generate 6 character code using letters and numbers
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Store code in Redis with expiration
        redis_key = f"reset_token:{email}"
        try:
            await redis_async.setex(
                redis_key,
                settings.RESET_TOKEN_EXPIRE_MINUTES * 60,
                code
            )
        except Exception as redis_error:
            logger.error(f"Redis error: {redis_error}")
            raise Exception("Error storing reset code")
        
        return code
        
    except Exception as e:
        logger.error(f"Code generation error: {str(e)}")
        raise

async def verify_reset_token(email: str, otp: str) -> bool:
    """Verify the OTP code for password reset."""
    try:
        # Get stored OTP from Redis
        redis_key = f"reset_token:{email}"
        stored_otp = await redis_async.get(redis_key)
        
        if not stored_otp:
            logger.warning(f"No OTP found for email: {email}")
            return False
            
        # Convert bytes to string if necessary
        if isinstance(stored_otp, bytes):
            stored_otp = stored_otp.decode('utf-8')
            
        # Compare stored OTP with provided OTP
        is_valid = stored_otp == otp
        
        if is_valid:
            # Delete the OTP after successful verification
            await redis_async.delete(redis_key)
            
        return is_valid
        
    except Exception as e:
        logger.error(f"OTP verification error: {str(e)}")
        raise
