# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

**FinControl** — Aplicación personal de análisis financiero con dashboard interactivo, simulador hipotecario, predicciones con IA y análisis de escenarios.

## Comandos de desarrollo

### Iniciar entorno

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

### Servicios disponibles

- Backend API + Swagger: http://localhost:8000/docs
- Frontend (pendiente): http://localhost:3000
- ML Service (pendiente): http://localhost:8001/docs

### Tests

```bash
# Todos los tests
docker compose -f docker-compose.dev.yml exec backend pytest

# Test específico
docker compose -f docker-compose.dev.yml exec backend pytest tests/test_auth.py -v

# Con cobertura
docker compose -f docker-compose.dev.yml exec backend pytest --cov=app
```

### Lint y formato (Ruff)

```bash
# Verificar
docker compose -f docker-compose.dev.yml exec backend ruff check app/

# Corregir y formatear
docker compose -f docker-compose.dev.yml exec backend ruff format app/
docker compose -f docker-compose.dev.yml exec backend ruff check --fix app/
```

### Sin Docker (desarrollo local)

```bash
cd backend
python3.12 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
ruff check app/
pytest
```

### Migraciones Alembic

```bash
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "descripcion"
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

## Arquitectura

### Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery + Redis
- **Frontend:** SvelteKit, TypeScript, Apache ECharts, Skeleton UI
- **BD:** PostgreSQL 16 (principal), Redis 7 (cache + broker Celery)
- **ML:** DistilBERT (categorización), LSTM + PyTorch (predicciones), Prophet (baseline), NumPy/SciPy (cálculos hipotecarios)
- **Infra:** Docker Compose, Nginx

### Estructura del backend (`backend/app/`)

```
main.py          # Punto de entrada FastAPI, CORS, health check GET /health
config.py        # Settings pydantic-settings (carga .env), property database_url
database.py      # Engine SQLAlchemy async, get_db dependency
models/          # Modelos SQLAlchemy: User, Account, Transaction, Budget, Investment,
                 #   MortgageSim, Category, MLModel, Scenario, TaxConfig
schemas/         # Schemas Pydantic (validación entrada/salida)
api/v1/          # Endpoints REST por dominio (auth, accounts, transactions, budgets,
                 #   investments, mortgage, analytics, ml, tax)
services/        # Lógica de negocio desacoplada de la BD
tasks/           # Tareas Celery (reentrenamiento ML mensual, cálculos periódicos)
utils/           # Funciones financieras: TIR, VAN, amortización, Monte Carlo
```

### Flujo de una request

```
Request → CORS Middleware → api/v1/{dominio}
  → Dependencias (get_current_user, get_db)
  → Service Layer (validación + lógica)
  → SQLAlchemy async → PostgreSQL
  → Response (schema Pydantic serializado)
```

### Estrategia ML

- **Categorización (DistilBERT):** umbral >0.92 auto-asigna, >0.5 sugiere, <0.5 manual. Feedback del usuario genera reentrenamiento.
- **Predicción cashflow (LSTM):** features: ingresos/gastos, categoría, mes, Euríbor. Reentrenamiento mensual via Celery Beat.
- **Escenarios "what-if":** motor reglas + Monte Carlo, output en percentiles P10/P50/P90.

### Estado actual del proyecto

`main.py`, `config.py`, `database.py` y `utils/logging.py` ya estaban implementados. Con la **Fase 1.2** se añadió autenticación JWT completa. Con la **Fase 1.3** se han añadido:

- `models/account.py`, `models/category.py`, `models/transaction.py` — modelos SQLAlchemy
- `schemas/accounts.py`, `schemas/categories.py`, `schemas/transactions.py` — schemas Pydantic
- `services/accounts.py`, `services/categories.py` (con seeder), `services/transactions.py` — lógica de negocio
- `api/v1/accounts.py`, `api/v1/categories.py`, `api/v1/transactions.py` — routers CRUD
- `alembic/versions/0002_add_accounts_categories_transactions.py` — migración
- Seeder de categorías por defecto ejecutado en lifespan de FastAPI

Con la **Fase 1.4** se han añadido:

- `utils/csv_parser.py` — Parser para formato CSV de OpenBank (separador `;`, fecha DD/MM/YYYY, coma decimal, encoding UTF-8/latin-1)
- `schemas/imports.py` — Schemas Pydantic: `ImportResult`, `ImportRowResult`, `ImportRowStatus`
- `services/imports.py` — Lógica de importación con deduplicación y modo dry_run
- `api/v1/transactions.py` — Endpoint `POST /transactions/import/csv` (query params: `account_id`, `dry_run`)
- `tests/fixtures/openbank_sample.csv` — CSV de muestra para tests
- `tests/test_imports.py` — 11 tests de importación

Con la **Fase 2.1** se han añadido:

- `models/budget.py` — modelos `Budget` y `BudgetAlert` con `UniqueConstraint(user_id, category_id, period_year, period_month)`
- `schemas/budgets.py` — schemas Pydantic: `BudgetCreate`, `BudgetUpdate`, `BudgetResponse`, `BudgetStatusResponse`, `BudgetAlertResponse`
- `services/budgets.py` — lógica CRUD + `get_budget_status` (suma gastos del período, calcula % consumido, crea alertas al superar el umbral configurable) + `list_alerts`/`mark_alert_read`
- `api/v1/budgets.py` — router con 9 endpoints (CRUD + `/{id}/status` + `/status` listado por período + `/alerts` + `/alerts/{id}/read`)
- `alembic/versions/0003_add_budgets.py` — migración tablas `budgets` y `budget_alerts`
- `tests/test_budgets.py` — 18 tests
- `docker-compose.dev.yml` — añadido volume mount `./backend/tests:/app/tests`

Con la **Fase 2.2** se han añadido:

- `models/investment.py` — modelo `Investment` (depósitos, fondos, acciones, bonos) con campos: `investment_type`, `principal_amount`, `interest_rate`, `interest_type` (simple/compound), `compounding_frequency`, `start_date`, `maturity_date`, `auto_renew`, `renewal_period_months`, `renewals_count`, `current_value`
- `schemas/investments.py` — schemas Pydantic: `InvestmentCreate` (con `@model_validator` para validar compound+frequency y maturity>start), `InvestmentUpdate`, `InvestmentResponse`, `InvestmentStatusResponse`, `InvestmentSummaryResponse`
- `services/investments.py` — lógica CRUD + `_calculate_return` (interés simple y compuesto) + `get_investment_status` (rendimiento acumulado a día de hoy) + `renew_investment` (extiende maturity_date) + `get_investment_summary` (totales agregados)
- `api/v1/investments.py` — router con 8 endpoints: `GET /summary`, `POST /`, `GET /`, `GET /{id}`, `GET /{id}/status`, `PATCH /{id}`, `DELETE /{id}`, `POST /{id}/renew`
- `alembic/versions/0004_add_investments.py` — migración tabla `investments`
- `tests/test_investments.py` — 23 tests

Con la **Fase 2.3** se han añadido:

- `schemas/analytics.py` — schemas Pydantic: `OverviewResponse`, `CashflowMonthResponse`, `CategoryExpenseResponse`, `SavingsRateMonthResponse`, `TrendsResponse`
- `services/analytics.py` — lógica de agregación con SQLAlchemy async: `get_overview` (ingresos/gastos/ahorro/balance total de cuentas activas), `get_cashflow` (últimos N meses con ceros para meses sin datos), `get_expenses_by_category` (agrupado con % del total), `get_savings_rate` (tasa mensual + medias móviles 3m y 6m), `get_trends` (cambio % vs mes anterior y vs media 12 meses)
- `api/v1/analytics.py` — router con 5 endpoints GET bajo `/analytics` (overview, cashflow, expenses-by-category, savings-rate, trends)
- `tests/test_analytics.py` — 21 tests de integración

Con la **Fase 2.5** se han añadido:

- `models/tax.py` — modelos `TaxBracket` (tramos IRPF, tabla sistema, seeded) y `TaxConfig` (configuración bruto por usuario y año, `UniqueConstraint(user_id, tax_year)`)
- `schemas/tax.py` — schemas Pydantic: `TaxBracketResponse`, `TaxConfigCreate/Update/Response`, `BracketBreakdown`, `TaxCalculationResponse`
- `services/tax.py` — lógica: `seed_tax_brackets` (idempotente, 2025/2026 general+ahorro), CRUD de TaxConfig, `calculate_tax` (bruto→neto: SS 6.35%/6.50% según año, base máxima mensual, reducción trabajo 2.000€, mínimo personal 5.550€, tramos progresivos)
- `api/v1/tax.py` — router con 7 endpoints bajo `/tax`: `GET /brackets`, `POST /configs`, `GET /configs`, `GET /configs/{id}`, `GET /configs/{id}/calculation`, `PATCH /configs/{id}`, `DELETE /configs/{id}`
- `alembic/versions/0006_add_tax.py` — migración tablas `tax_brackets` y `tax_configs`
- `tests/test_tax.py` — 26 tests de integración
- `services/mortgage.py` y `api/v1/mortgage.py` — parámetro opcional `tax_config_id` en `GET /mortgage/affordability` para usar salario neto real en vez de ingresos de transacciones
- `tests/conftest.py` — se añade llamada al seeder de tramos IRPF en la fixture de test (junto al seeder de categorías)

Con la **Fase 2.4** se han añadido:

- `utils/mortgage.py` — Motor de cálculo hipotecario puro (sin BD): `monthly_payment` (PMT sistema francés), `amortization_schedule` (fijo/variable/mixto con revisión anual o semestral), `effective_annual_rate` (TAE via Newton-Raphson), `closing_costs` (notaría, registro, ITP/AJD, gestoría, tasación)
- `schemas/mortgage.py` — Schemas Pydantic: `MortgageSimulateRequest` (con `@model_validator` para validar campos por tipo), `MortgageSimulationResult`, `AmortizationRowSchema`, `ClosingCostsSchema`, `MortgageCompareRequest/Response`, `ScenarioParams`, `AffordabilityResponse`, `MaxLoanOption`, `MortgageSaveRequest`, `MortgageSimulationResponse`
- `services/mortgage.py` — Lógica de negocio: `simulate_mortgage` (stateless), `compare_scenarios` (compara hasta 5 escenarios), `get_affordability` (regla 35% sobre ingresos reales de analytics), CRUD de simulaciones guardadas
- `api/v1/mortgage.py` — Router con 7 endpoints bajo `/mortgage`: `POST /simulate`, `POST /compare`, `GET /affordability`, `POST /simulations`, `GET /simulations`, `GET /simulations/{id}`, `DELETE /simulations/{id}`
- `models/mortgage.py` — Modelo SQLAlchemy `MortgageSimulation` con parámetros de entrada y resultados pre-calculados
- `alembic/versions/0005_add_mortgage_simulations.py` — Migración tabla `mortgage_simulations`
- `tests/test_mortgage.py` — 26 tests de integración

Con la **Fase 3.1** se han añadido:

- `ml-service/` — Microservicio FastAPI dedicado a ML (port 8001), independiente del backend
- `ml-service/Dockerfile` — Imagen base `pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime`, usuario no-root
- `ml-service/app/main.py` — App FastAPI con middleware de logging estructurado y lifespan (placeholder para carga de modelo en Fase 3.2)
- `ml-service/app/config.py` — Settings: `model_path`, `categorization_threshold` (0.92), `categorization_suggest_threshold` (0.5), `redis_url` (db 3)
- `ml-service/app/routers/health.py` — `GET /health` (stub: `model_loaded=False`)
- `ml-service/app/routers/predict.py` — `POST /predict` (stub: devuelve respuesta sin modelo cargado)
- `ml-service/app/routers/feedback.py` — `POST /feedback` (registra evento en log; almacenamiento pendiente en Fase 3.3)
- `ml-service/app/routers/model.py` — `GET /model/status` (stub: `loaded=False`)
- `ml-service/app/schemas/` — `PredictRequest/Response`, `FeedbackRequest/Response`, `ModelStatusResponse`
- `backend/app/schemas/ml.py` — `MLPredictRequest/Response`, `MLFeedbackRequest/Response` (campo `ml_available` para degradación graceful)
- `backend/app/services/ml_client.py` — `MLClient`: cliente HTTP async con degradación graceful (si el servicio no está disponible devuelve respuestas stub sin interrumpir el flujo principal)
- `backend/app/api/v1/ml.py` — Router con 3 endpoints protegidos: `POST /ml/predict`, `POST /ml/feedback`, `GET /ml/status`
- `docker-compose.dev.yml` — ml-service con soporte GPU (`nvidia` runtime), volume persistente `ml_models:/app/models`, health check, dependencia de Redis
- `ml-service/tests/test_health.py`, `ml-service/tests/test_predict.py` — 9 tests de infraestructura (stubs + validaciones)
- `backend/tests/test_ml_client.py` — Tests del cliente ML con mock `respx` (sin dependencia del servicio real)

Con la **Fase 3.2** se han añadido:

- `ml-service/app/ml/__init__.py` — módulo ML
- `ml-service/app/ml/categories.py` — catálogo fijo de 10 categorías del sistema con mapeo índice↔nombre (ML service no tiene acceso a BD)
- `ml-service/app/ml/preprocessor.py` — `normalize_banking_text()`: normaliza texto bancario (referencias numéricas, fechas, ruido)
- `ml-service/app/ml/model_manager.py` — `ModelManager`: singleton que carga DistilBERT desde `/app/models/categorizer/`, expone `predict()` y `get_status()`; modo degradado si no hay modelo
- `ml-service/data/synthetic_dataset.py` — genera `data/dataset.json` con ~800 ejemplos de transacciones bancarias españolas (80 por categoría)
- `ml-service/scripts/train.py` — fine-tuning de `distilbert-base-multilingual-cased` con el dataset; guarda modelo + metadata en `/app/models/categorizer/`
- `ml-service/app/routers/predict.py` — stub reemplazado: inferencia real via `ModelManager.predict()`; thresholds 0.92/0.5 configurables
- `ml-service/app/routers/feedback.py` — stub reemplazado: almacena feedback en Redis (lista `ml:feedback`) para reentrenamiento (Fase 3.3)
- `ml-service/app/routers/health.py`, `model.py` — actualizados con estado real de `ModelManager`
- `ml-service/app/main.py` — lifespan carga `ModelManager` e inyecta en `app.state.model_manager`
- `ml-service/app/config.py` — añadido campo `device: str = "cpu"` (soporte GPU/CPU)
- `ml-service/pyproject.toml` — corrección build backend a `setuptools.build_meta` (compatible con Python 3.11 de la imagen pytorch)
- `ml-service/tests/conftest.py` — inicializa `ModelManager` degradado en `app.state` antes de los tests (ASGITransport no dispara lifespan)
- `ml-service/tests/test_predict.py` — actualizado a comportamiento modo degradado (`model_version="degraded"`, `status in ("stored","queued")`)
- `ml-service/tests/test_categorization.py` — 18 nuevos tests: catálogo de categorías, preprocessor, ModelManager degradado, endpoints API
- `backend/app/schemas/transactions.py` — `TransactionResponse` añade `ml_suggested_category_id: UUID | None` y `ml_confidence: float | None`
- `backend/app/services/transactions.py` — nueva función `create_transaction_with_ml()`: crea transacción y llama ML; auto-asigna categoría si confianza > 0.92, devuelve sugerencia si > 0.5
- `backend/app/api/v1/transactions.py` — `POST /transactions` usa `create_transaction_with_ml()` en lugar de `create_transaction()`
- `backend/tests/test_transactions.py` — 5 nuevos tests de integración ML con respx (auto-asignación, sugerencia, campos ML en respuesta, skip cuando hay categoría explícita)

Con la **Fase 3.3** se han añadido:

- `ml-service/app/ml/trainer.py` — Módulo reutilizable: `build_training_examples` (dataset base + feedback Redis), `run_incremental_retrain` (fine-tune desde modelo activo), `get_next_version`, `evaluate`, `train_val_split`
- `ml-service/scripts/train.py` — Refactorizado para importar de `app.ml.trainer`; sigue funcionando como CLI
- `ml-service/app/ml/model_manager.py` — Añadido `async reload()` para recargar modelo en caliente
- `ml-service/app/schemas/model.py` — `ModelStatusResponse` añade `retrain_in_progress: bool`
- `ml-service/app/schemas/retrain.py` — `RetrainResponse(status, feedback_count, reason?, model_version?)`
- `ml-service/app/routers/model.py` — `GET /model/status` lee `feedback_count` real de Redis y `retrain_in_progress` desde `app.state`
- `ml-service/app/routers/retrain.py` — `POST /retrain`: lee feedback Redis, verifica umbrales, lanza training en ThreadPoolExecutor, devuelve 202. Callback promueve candidato si accuracy ≥ activo−2%, descarta si no. History en `/app/models/history/`.
- `ml-service/app/config.py` — Añadidos: `min_feedback_for_retrain=10`, `retrain_epochs=2`, `retrain_batch_size=16`
- `ml-service/app/main.py` — Registrado router `retrain`, inicializado `app.state.retrain_in_progress=False`
- `backend/app/tasks/celery_app.py` — Instancia `Celery` + `beat_schedule` semanal (domingo 3AM, configurable)
- `backend/app/tasks/__init__.py` — Exporta `celery_app` para que `celery -A app.tasks` funcione
- `backend/app/tasks/ml_retraining.py` — Task `trigger_ml_retrain`: llama `ml_client.trigger_retrain_sync()`, degradación graceful
- `backend/app/services/ml_client.py` — Añadido `trigger_retrain_sync()` síncrono para uso desde Celery
- `backend/app/config.py` — Añadidos: `ml_retrain_min_feedback`, `ml_retrain_schedule_hour`, `ml_retrain_schedule_day_of_week`
- `ml-service/tests/test_trainer.py` — 11 tests unitarios del módulo trainer
- `ml-service/tests/test_retrain.py` — 12 tests del endpoint `/retrain` y callbacks
- `backend/tests/test_celery_tasks.py` — 7 tests de `trigger_retrain_sync` y la Celery task

Con la **Fase 4.1** se han añadido:

- `ml-service/app/ml/lstm_model.py` — Arquitectura `CashflowLSTM`: LSTM bidireccional (2 capas, hidden=64, MC Dropout para intervalos de confianza)
- `ml-service/app/ml/forecaster.py` — Singleton `Forecaster` (patrón análogo a `ModelManager`): carga LSTM desde disco, Prophet como fallback, modo degradado con ceros
- `ml-service/app/schemas/forecast.py` — Schemas: `MonthlyPoint`, `ForecastPoint`, `ForecastRequest`, `ForecastResponse`, `ForecastRetrainResponse`, `ForecastStatusResponse`
- `ml-service/app/routers/forecast.py` — Router con 3 endpoints: `POST /forecast` (inferencia), `POST /forecast/retrain` (reentrenamiento async en ThreadPoolExecutor), `GET /forecast/status`
- `ml-service/data/generate_timeseries.py` — Generador de dataset sintético (200 series × 36 meses, 5 perfiles de usuario españoles)
- `ml-service/scripts/train_forecaster.py` — CLI de entrenamiento inicial LSTM
- `ml-service/app/config.py` — Nuevos campos: `forecast_model_path`, `forecast_min_months`, `forecast_min_series_for_retrain`, `forecast_retrain_epochs/batch_size`
- `ml-service/pyproject.toml` — Nuevas dependencias: `scikit-learn>=1.4`, `prophet>=1.1`
- `ml-service/tests/test_forecast.py` — 15 tests (degraded mode, validación, schema, unitarios de Forecaster)
- `backend/app/schemas/forecasting.py` — `ForecastMonthResponse`, `CashflowForecastResponse`
- `backend/app/schemas/ml.py` — Añadidos `MLForecastPoint`, `MLForecastRequest`, `MLForecastResponse`
- `backend/app/services/forecasting.py` — `get_cashflow_forecast()`: obtiene historial via analytics + llama ml-service + degradación graceful
- `backend/app/services/ml_client.py` — Añadidos `forecast()` (async) y `trigger_forecast_retrain_sync()` (sync para Celery)
- `backend/app/api/v1/analytics.py` — Endpoint `GET /analytics/forecast?months=6`
- `backend/app/tasks/forecasting.py` — Celery task `trigger_forecast_retrain`
- `backend/app/tasks/celery_app.py` — Beat schedule mensual (1 de cada mes 4AM)
- `backend/app/config.py` — Nuevos campos: `ml_forecast_min_months`, `ml_forecast_max_ahead`, `ml_forecast_retrain_schedule_hour`
- `backend/tests/test_forecasting.py` — 11 tests de integración

Con la **Fase 4.3** se han añadido:

- `backend/app/schemas/mortgage.py` — Añadidos `StressTestResult` y `AIAffordabilityResponse`: respuesta del nuevo endpoint con ingresos predichos P10/P50/P90, max_loan por percentil, stress tests por nivel de Euríbor, comparación vs capacidad actual
- `backend/app/services/mortgage.py` — Nueva función `get_ai_affordability()`: pipeline de 6 pasos (capacidad actual, historial, forecast ML, ingresos promedio predichos, Euríbor base desde MortgageSimulation, stress tests). Reutiliza `_max_loan_for_payment`, `_irpf_monthly` (import local), `ml_client.forecast()` y `analytics_svc.get_cashflow()`. El flag `is_affordable` compara el pago del préstamo baseline (nivel 0) a la tasa estresada vs 35% del ingreso predicho P50.
- `backend/app/api/v1/mortgage.py` — Endpoint `GET /mortgage/ai-affordability` con query params: `months_ahead` (6-24), `term_years` (5-40), `tax_config_id`, `gross_annual`, `euribor_stress_levels` (lista de incrementos)
- `backend/app/config.py` — Nuevos campos: `ai_affordability_default_euribor` (3.5), `ai_affordability_default_spread` (0.8), `ai_affordability_monte_carlo_simulations` (1000)
- `backend/tests/test_mortgage.py` — 18 nuevos tests de integración con `respx` para mockear ml-service (auth, estructura, ML degradado, invariantes P10≤P50≤P90, Euríbor decreciente, is_affordable, validación, labels)

Con la **Fase 4.2** se han añadido:

- `backend/app/utils/monte_carlo.py` — Funciones puras NumPy: `simulate_net_distribution` (MC con σ estimado del intervalo P10/P90), `apply_scenario_modifications` (variaciones deterministas)
- `backend/app/schemas/scenarios.py` — Schemas Pydantic: `RecurringExpenseModification`, `ScenarioRequest` (salary_variation_pct, euribor_variation_pct, recurring_expense_modifications, gross_annual, tax_year, monte_carlo_simulations), `ScenarioMonthResult`, `ScenarioSummary`, `ScenarioResponse`
- `backend/app/services/scenarios.py` — Motor principal stateless: histórico → delta gastos → impacto Euríbor (busca MortgageSimulation variable/mixta) → forecast ML → IRPF puro → Monte Carlo por mes → resumen. Función `_irpf_monthly()` replica lógica de `services/tax.py` sin BD
- `backend/app/api/v1/scenarios.py` — Router `POST /scenarios/analyze` protegido con auth
- `backend/app/api/v1/__init__.py` — Registrado `scenarios.router`
- `backend/app/config.py` — Nuevo campo `scenario_monte_carlo_simulations=1000`
- `backend/tests/test_scenarios.py` — 19 tests (auth, variaciones de sueldo, gastos recurrentes, impacto fiscal, Euríbor sin hipoteca, degradación ML, validación, P10≤P50≤P90, funciones puras)

Los módulos `utils/` financieros (TIR, VAN) siguen sin implementar. Ver `Docs/ROADMAP.md` para el plan de 7 fases.

## Validación con tests

**Todo cambio o implementación debe ir acompañado de tests.** Antes de considerar cualquier tarea completada:

1. Escribir o actualizar los tests que cubran el código modificado.
2. Ejecutar los tests y verificar que todos pasan.
3. No se considera terminada ninguna implementación si no tiene tests que la validen.

```bash
# Ejecutar tests tras cada cambio
docker compose -f docker-compose.dev.yml exec backend pytest --cov=app -v
```

## Documentación

Con cada cambio significativo o al completar una fase del roadmap, actualizar:

- `Docs/ARCHITECTURE.md` — si cambia el stack, modelos de datos, endpoints o estrategia ML
- `Docs/ROADMAP.md` — marcar fases completadas y ajustar las siguientes
- `CLAUDE.md` — si cambia la estructura de módulos, comandos o el estado de implementación

## Configuración

- Variables de entorno en `.env` (copiar desde `.env.example`). La clase `Settings` en `config.py` las carga automáticamente.
- Ruff con `line-length = 100`, target Python 3.12, reglas: E, F, I, N, W, UP, B, SIM.
- pytest con `asyncio_mode = "auto"`, tests en `backend/tests/`.
- Documentación de arquitectura detallada en `Docs/ARCHITECTURE.md`; plan de desarrollo en `Docs/ROADMAP.md`.
