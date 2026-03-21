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

- **Categorización (DistilBERT):** umbral >0.85 auto-asigna, >0.5 sugiere, <0.5 manual. Feedback del usuario genera reentrenamiento.
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
- `ml-service/app/config.py` — Settings: `model_path`, `categorization_threshold` (0.85), `categorization_suggest_threshold` (0.5), `redis_url` (db 3)
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

Los módulos `tasks/` y `utils/` financieros (TIR, VAN, Monte Carlo) siguen sin implementar. Ver `Docs/ROADMAP.md` para el plan de 7 fases.

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
