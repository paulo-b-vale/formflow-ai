# app/config/settings.py
import sys
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Loads and validates application settings from environment variables."""
    # If pytest is running, change the database name
    DATABASE_NAME: str = "form_assistant_db_test" if "pytest" in sys.modules else "form_assistant_db"
    SECRET_KEY: str
    DEBUG: bool = True
    MONGODB_URL: str
    REDIS_URL: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    GEMINI_API_KEY: str
    UPLOAD_DIRECTORY: str = "/app/uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB default

    # LangSmith tracing settings
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "default"
    
    # S3 Configuration
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str
    S3_REGION_NAME: str
    S3_ENDPOINT_URL: str = None  # Leave empty for AWS S3, provide for MinIO or other S3-compatible services

    # Initial admin user settings
    INITIAL_ADMIN_EMAIL: str = "admin@example.com"
    INITIAL_ADMIN_PASSWORD: str = "admin123"
    INITIAL_ADMIN_NAME: str = "Admin User"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()