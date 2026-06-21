from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional

class Settings(BaseSettings):
    # Database Settings
    POSTGRES_USER: str = "fitness"
    POSTGRES_PASSWORD: str = "change_me_please"
    POSTGRES_DB: str = "fitness_os"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[str] = None

    # n8n Webhook Settings
    N8N_WEBHOOK_URL: Optional[str] = None
    N8N_AUTOFILL_WEBHOOK_URL: Optional[str] = None

    # App Settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # FITNESS_OS_API_KEY: A secret token used to authenticate clients.
    # The frontend fetches this from localStorage and sends it in the X-API-Key header.
    # It must be configured via the .env file. If not set, a placeholder is used for development/testing.
    FITNESS_OS_API_KEY: str = "change_me_api_key_fitness_os_123"

    @model_validator(mode="before")
    @classmethod
    def assemble_db_url(cls, data: any) -> any:
        # In pydantic settings before-validator, data is a dict of incoming fields
        if isinstance(data, dict):
            db_url = data.get("DATABASE_URL")
            if not db_url:
                user = data.get("POSTGRES_USER", "fitness")
                password = data.get("POSTGRES_PASSWORD", "change_me_please")
                host = data.get("POSTGRES_HOST", "db")
                port = data.get("POSTGRES_PORT", "5432")
                db = data.get("POSTGRES_DB", "fitness_os")
                data["DATABASE_URL"] = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
            
            # If FITNESS_OS_API_KEY is empty/blank in env, fallback to default key
            api_key = data.get("FITNESS_OS_API_KEY")
            if not api_key:
                data["FITNESS_OS_API_KEY"] = "change_me_api_key_fitness_os_123"
        return data

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
