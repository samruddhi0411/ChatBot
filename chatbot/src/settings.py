from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    google_api_key: str
    gemini_model: str = "gemini-1.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,   # accepts GOOGLE_API_KEY / GEMINI_MODEL
        env_ignore_empty=True,
    )

settings = Settings()
