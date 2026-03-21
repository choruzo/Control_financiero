from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FinControl ML Service"
    app_env: str = "development"
    debug: bool = True

    # ML
    model_path: str = "/app/models"
    categorization_threshold: float = 0.85
    categorization_suggest_threshold: float = 0.5

    # Redis (para almacenar feedback y estado del modelo)
    redis_url: str = "redis://redis:6379/3"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "env_prefix": "ML_"}


settings = Settings()
