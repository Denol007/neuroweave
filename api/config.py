from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://neuroweave:neuroweave@localhost:5432/neuroweave"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MongoDB (LangGraph checkpoints)
    MONGODB_URI: str = "mongodb://localhost:27017"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Discord
    DISCORD_BOT_TOKEN: str = ""
    DISCORD_CLIENT_ID: str = ""
    DISCORD_CLIENT_SECRET: str = ""

    # GitHub
    GITHUB_TOKEN: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "neuroweave-extraction"

    # App
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "change-me-in-production"
    CORS_ORIGINS: str = "http://localhost:3000"


settings = Settings()
