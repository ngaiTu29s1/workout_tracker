from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database Settings
    POSTGRES_USER: str = "fitness"
    POSTGRES_PASSWORD: str = "change_me_please"
    POSTGRES_DB: str = "fitness_os"
    DATABASE_URL: str = "postgresql+asyncpg://fitness:change_me_please@db:5432/fitness_os"

    # n8n Webhook Settings
    N8N_WEBHOOK_URL: str = "http://n8n.local:5678/webhooks/enrich"

    # App Settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
