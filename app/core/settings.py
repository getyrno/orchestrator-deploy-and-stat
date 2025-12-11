from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    github_webhook_secret: str
    telegram_token: str

    class Config:
        env_file = ".env.local"

settings = Settings()
