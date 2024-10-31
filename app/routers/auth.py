from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import UserCreate, User, Token, PasswordResetRequest, PasswordResetResponse
from app.services.auth import (
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.services.email_service import send_reset_email
from app.services.token_service import generate_reset_token
import logging


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register")
async def register(user: UserCreate):
    new_user = await create_user(user)
    print(new_user)
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer", "username": new_user.email, "id": new_user.id}

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

@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks
):
    """Handle forgot password requests."""
    try:
        # Generate reset token
        reset_token = await generate_reset_token(request.email)
        
        # Send email in background
        background_tasks.add_task(
            send_reset_email,
            request.email,
            reset_token
        )
        
        logger.info(f"Password reset initiated for {request.email}")
        
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
