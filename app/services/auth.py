from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.database import get_collection
from app.config import settings
from pydantic import EmailStr
from app.services.token_service import verify_reset_token
from app.models.user import UserCreate, UserInDB, User, TokenData, GoogleAuthData


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def create_user(user: UserCreate):
    users = get_collection("users")
    existing_user = await users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user.model_dump()
    
    # Handle password for email users
    if user.auth_provider == "email":
        if not user.password:
            raise HTTPException(status_code=400, detail="Password required for email registration")
        hashed_password = pwd_context.hash(user.password)
        user_dict["hashed_password"] = hashed_password
        user_dict.pop('password', None)
    
    result = await users.insert_one(user_dict)
    created_user = await users.find_one({"_id": result.inserted_id})
    return User(**created_user, id=str(created_user["_id"]))

async def authenticate_google_user(google_data: GoogleAuthData) -> User:
    """Authenticate or create user with Google data"""
    users = get_collection("users")
    existing_user = await users.find_one({"email": google_data.email})
    
    if existing_user:
        # Update existing user's Google info
        await users.update_one(
            {"email": google_data.email},
            {"$set": {
                "name": google_data.name,
                "profile_picture": google_data.image,
                "auth_provider": "google"
            }}
        )
        return User(**existing_user, id=str(existing_user["_id"]))
    
    # Create new user
    new_user = UserCreate(
        email=google_data.email,
        name=google_data.name,
        profile_picture=google_data.image,
        auth_provider="google"
    )
    return await create_user(new_user)

async def authenticate_user(email: EmailStr, password: str):
    users = get_collection("users")
    user = await users.find_one({"email": email})
    if not user or not pwd_context.verify(password, user["hashed_password"]):
        return False
    return User(**user, id=str(user["_id"]))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload["sub"]
        if username is None:
            print("all good")
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    users = get_collection("users")
    user = await users.find_one({"email": token_data.username})
    if user is None:
        raise credentials_exception
    return User(**user, id=str(user["_id"]))

async def reset_password(email: EmailStr, otp: str, new_password: str):
    """Reset user password with OTP verification."""
    users = get_collection("users")
    
    # Verify the reset token
    is_valid = await verify_reset_token(email, otp)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Hash the new password
    hashed_password = pwd_context.hash(new_password)
    
    # Update the user's password
    result = await users.update_one(
        {"email": email},
        {"$set": {"hashed_password": hashed_password}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return True
