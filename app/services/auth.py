from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.models.user import UserCreate, UserInDB, User, TokenData
from app.database import get_collection
from app.config import settings
from bson import ObjectId
from pydantic import EmailStr

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def create_user(user: UserCreate):
    users = get_collection("users")
    existing_user = await users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = pwd_context.hash(user.password)
    user_in_db = UserInDB(**user.dict(), hashed_password=hashed_password)
    result = await users.insert_one(user_in_db.dict())
    created_user = await users.find_one({"_id": result.inserted_id})
    return User(**created_user, id=str(created_user["_id"]))

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
