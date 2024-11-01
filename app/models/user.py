from pydantic import BaseModel, EmailStr
from typing import Optional, Literal

class UserBase(BaseModel):
    email: EmailStr
    name: str
    profile_picture: Optional[str] = None
    auth_provider: Optional[str] = "email"  # "email" or "google"

class UserCreate(UserBase):
    password: Optional[str] = None  # Optional because Google users won't have a password

class UserInDB(UserBase):
    hashed_password: Optional[str] = None  # Optional for Google users

class User(UserBase):
    id: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    id: str

class TokenData(BaseModel):
    username: Optional[str] = None
    auth_provider: Optional[str] = None

class GoogleAuthData(BaseModel):
    email: str
    name: str
    image: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetResponse(BaseModel):
    message: str

class PasswordReset(BaseModel):
    email: EmailStr
    otp: str
    new_password: str
    confirm_password: str
