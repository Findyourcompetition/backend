from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from app.services.email_service import send_reset_email
from app.services.token_service import generate_reset_token
import logging
from app.models.user import (
    UserCreate, User, Token, PasswordResetRequest, 
    PasswordResetResponse, PasswordReset, GoogleAuthData
)
from app.services.auth import (
    create_user, authenticate_user, create_access_token,
    get_current_user, reset_password, authenticate_google_user
)
from app.database import get_collection, redis_client
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/register")
async def register(user: UserCreate):
    new_user = await create_user(user)
    print(new_user)
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer", "username": new_user.email, "id": new_user.id}

@router.post("/google/login", response_model=Token)
async def google_login(google_data: GoogleAuthData):
    """Handle Google Sign-In"""
    try:
        user = await authenticate_google_user(google_data)
        access_token = create_access_token(
            data={
                "sub": user.email,
                "auth_provider": "google"
            }
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.email,
            "id": user.id
        }
    except Exception as e:
        logger.error(f"Google login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not handle Google login"
        )

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "username": user.email, "id": user.id}

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """Handle logout for both traditional and Google auth"""
    try:
        # Add token to blacklist
        redis_key = f"blacklist_token:{token}"
        redis_client.set(
            redis_key,
            "true",
            ex=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during logout"
        )

@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks
):
    """Handle forgot password requests."""
    try:
        # Check if user exists (but don't reveal this in the response)
        users = get_collection("users")
        user = await users.find_one({"email": request.email})
        
        if user:
            # Generate reset token
            reset_token = await generate_reset_token(request.email)
            
            # Send email in background
            background_tasks.add_task(
                send_reset_email,
                request.email,
                reset_token
            )
            
            logger.info(f"Password reset initiated for {request.email}")
        else:
            logger.info(f"Password reset attempted for non-existent email: {request.email}")
        
        # Always return the same message for security
        return PasswordResetResponse(
            message="If an account exists with this email, "
                   "you will receive password reset instructions."
        )
        
    except Exception as e:
        logger.error(f"Error in forgot password flow: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error processing password reset request"
        )

@router.post("/reset-password")
async def reset_password_endpoint(reset_data: PasswordReset):
    """Reset user password with OTP verification."""
    if reset_data.new_password != reset_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )
    
    try:
        await reset_password(
            reset_data.email,
            reset_data.otp,
            reset_data.new_password
        )
        
        logger.info(f"Password reset successful for {reset_data.email}")
        
        return {"message": "Password reset successful"}
        
    except Exception as e:
        logger.error(f"Error in password reset: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error processing password reset"
        )
