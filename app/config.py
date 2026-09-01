from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GOOGLE_PLACES_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Your Name"
    SMTP_FROM_EMAIL: str = ""

    DATABASE_URL: str = "sqlite:///./leadgen.db"
    AUTOMATION_LEVEL: str = "manual"  # "manual" = every email needs human approval before send


settings = Settings()
