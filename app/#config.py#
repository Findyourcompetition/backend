# app/config.py
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Existing settings
    MONGODB_URL: str = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/fyc")
    DATABASE_NAME: str = "fyc_prod_db"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    OPENAI_API_KEY: str

    # Email settings
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    RESET_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True  # Make sure environment variables are case-sensitive

# Initialize the settings object
settings = Settings()
