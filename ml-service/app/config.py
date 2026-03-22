from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FinControl ML Service"
    app_env: str = "development"
    debug: bool = True

    # ML (categorización)
    model_path: str = "/app/models"
    device: str = "cpu"
    categorization_threshold: float = 0.92
    categorization_suggest_threshold: float = 0.5

    # Redis (para almacenar feedback y estado del modelo)
    redis_url: str = "redis://redis:6379/3"

    # Reentrenamiento incremental (categorización)
    min_feedback_for_retrain: int = 10
    retrain_epochs: int = 2
    retrain_batch_size: int = 16

    # Forecasting (LSTM)
    forecast_model_path: str = "/app/models"
    forecast_min_months: int = 6          # mínimo de meses históricos recomendados
    forecast_max_months_ahead: int = 12   # máximo meses a predecir
    forecast_min_series_for_retrain: int = 3  # series mínimas para disparar retrain
    forecast_retrain_epochs: int = 20
    forecast_retrain_batch_size: int = 16

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "env_prefix": "ML_"}


settings = Settings()
