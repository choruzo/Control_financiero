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

Los módulos `tasks/` y `utils/` financieros (TIR, VAN, amortización, Monte Carlo) siguen sin implementar. Ver `Docs/ROADMAP.md` para el plan de 7 fases.

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
