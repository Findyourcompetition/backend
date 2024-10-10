from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    MONGODB_URL: str = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/fyc")
    DATABASE_NAME: str = "fyc_prod_db"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"  # Pydantic will automatically load from this file if present

# Initialize the settings object
settings = Settings()
