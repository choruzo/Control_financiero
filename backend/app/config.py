from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "FinControl"
    app_env: str = "development"
    debug: bool = True

    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "fincontrol"
    postgres_user: str = "fincontrol"
    postgres_password: str = "changeme"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # ML Service
    ml_service_url: str = "http://ml-service:8001"
    ml_categorization_threshold: float = 0.85

    # Celery
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # ML reentrenamiento automático (categorización)
    ml_retrain_min_feedback: int = 10
    ml_retrain_schedule_hour: int = 3
    ml_retrain_schedule_day_of_week: str = "0"

    # ML forecasting
    ml_forecast_min_months: int = 6         # mínimo meses históricos recomendados
    ml_forecast_max_ahead: int = 12         # máximo meses a predecir
    ml_forecast_retrain_schedule_hour: int = 4  # hora del reentrenamiento mensual (4AM)

    # Escenarios Monte Carlo
    scenario_monte_carlo_simulations: int = 1000

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
