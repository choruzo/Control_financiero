# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

**FinControl** — Aplicación personal de análisis financiero con dashboard interactivo, simulador hipotecario, predicciones con IA y análisis de escenarios.

## Comandos de desarrollo

```bash
# Iniciar entorno
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build

# Tests
docker compose -f docker-compose.dev.yml exec backend pytest
docker compose -f docker-compose.dev.yml exec backend pytest tests/test_auth.py -v
docker compose -f docker-compose.dev.yml exec backend pytest --cov=app

# Lint y formato (Ruff — Python)
docker compose -f docker-compose.dev.yml exec backend ruff check app/
docker compose -f docker-compose.dev.yml exec backend ruff format app/
docker compose -f docker-compose.dev.yml exec backend ruff check --fix app/

# Lint y formato (ESLint + Prettier — Frontend)
cd frontend && npm run lint
cd frontend && npm run lint:fix
cd frontend && npm run format
cd frontend && npm run format:check

# Tests E2E (Playwright)
cd frontend && npm run test:e2e
cd frontend && npm run test:e2e:ui   # modo interactivo

# Sin Docker
cd backend && python3.12 -m venv venv && source venv/bin/activate
pip install -e ".[dev]" && ruff check app/ && pytest

# Migraciones Alembic
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "descripcion"
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

### Servicios disponibles

- Backend API + Swagger: http://localhost:8000/docs
- Frontend: http://localhost:3000
- ML Service: http://localhost:8001/docs

## Arquitectura

### Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery + Redis
- **Frontend:** SvelteKit, TypeScript, Apache ECharts, Skeleton UI v2 (Svelte 4, `@sveltejs/kit` pinado a `2.12.1`)
- **BD:** PostgreSQL 16 (principal), Redis 7 (cache + broker Celery)
- **ML:** DistilBERT (categorización), LSTM + PyTorch (predicciones), Prophet (baseline), NumPy/SciPy (cálculos hipotecarios)
- **Infra:** Docker Compose, Nginx

### Estructura del backend (`backend/app/`)

```
main.py          # Punto de entrada FastAPI, CORS, health check GET /health
config.py        # Settings pydantic-settings (carga .env), property database_url
database.py      # Engine SQLAlchemy async, get_db dependency
models/          # User, Account, Transaction, Budget, Investment, MortgageSim, Category, MLModel, Scenario, TaxConfig
schemas/         # Schemas Pydantic (validación entrada/salida)
api/v1/          # Endpoints REST: auth, accounts, transactions, budgets, investments, mortgage, analytics, ml, tax, scenarios
services/        # Lógica de negocio desacoplada de la BD
tasks/           # Tareas Celery (reentrenamiento ML mensual, forecasting)
utils/           # Funciones financieras: amortización, Monte Carlo, csv_parser
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

- **Categorización (DistilBERT):** umbral >0.92 auto-asigna, >0.5 sugiere, <0.5 manual. Feedback genera reentrenamiento.
- **Predicción cashflow (LSTM):** features: ingresos/gastos, categoría, mes, Euríbor. Reentrenamiento mensual via Celery Beat.
- **Escenarios "what-if":** motor reglas + Monte Carlo, output en percentiles P10/P50/P90.

## Estado de implementación (fases completadas)

- **Fase 1.2** — Autenticación JWT completa (login, register, refresh, get_me).
- **Fase 1.3** — CRUD de cuentas, categorías (con seeder) y transacciones.
- **Fase 1.4** — Importación CSV OpenBank con deduplicación y modo dry_run (`POST /transactions/import/csv`).
- **Fase 2.1** — Presupuestos con alertas configurables por categoría y período (`/budgets`).
- **Fase 2.2** — Inversiones (depósitos, fondos, acciones, bonos) con interés simple/compuesto y renovación (`/investments`).
- **Fase 2.3** — Analytics: overview, cashflow mensual, gastos por categoría, tasa de ahorro y tendencias (`/analytics`).
- **Fase 2.4** — Simulador hipotecario: amortización fijo/variable/mixto, TAE, gastos de cierre, comparador, capacidad de endeudamiento (`/mortgage`).
- **Fase 2.5** — Cálculo IRPF: tramos 2025/2026, SS, mínimo personal, reducción trabajo; integrado con hipoteca (`/tax`).
- **Fase 3.1** — Microservicio ML independiente en puerto 8001 con endpoints stub y degradación graceful.
- **Fase 3.2** — DistilBERT real: fine-tuning sobre dataset sintético (~800 ejemplos), inferencia con thresholds, integración en `POST /transactions`.
- **Fase 3.3** — Reentrenamiento incremental del categorizador: feedback Redis → trainer → hot-reload; Celery beat semanal.
- **Fase 4.1** — Forecaster LSTM bidireccional (MC Dropout, P10/P50/P90) con Prophet fallback; endpoint `GET /analytics/forecast`.
- **Fase 4.2** — Motor de escenarios what-if: variaciones de sueldo, Euríbor y gastos recurrentes con Monte Carlo (`POST /scenarios/analyze`).
- **Fase 4.3** — Capacidad hipotecaria con IA: forecast ML + stress tests de Euríbor + IRPF integrado (`GET /mortgage/ai-affordability`).
- **Fase 5.1** — Frontend SvelteKit: autenticación, auth guard, layout AppShell con sidebar responsivo.
- **Fase 5.2** — Dashboard: 4 KPIs, gráfico cashflow ECharts, donut gastos por categoría, alertas y transacciones recientes.
- **Fase 5.3** — Página de transacciones: tabla filtrable/paginada, badges ML IA/Sugerida, importación CSV 3 pasos, feedback ML inline.
- **Fase 5.4** — Página de presupuestos: cards con semáforo, historial 3 meses, gráfico comparativo, CRUD modal.
- **Fase 5.5** — Página de inversiones: cards por tipo, timeline Gantt vencimientos, rendimiento bajo demanda, renovación.
- **Fase 5.6** — Página de hipoteca: simulador fijo/variable/mixto, comparador hasta 3 escenarios, capacidad, guardadas.
- **Fase 5.7** — Página de predicciones: forecast P10/P50/P90 con bandas, escenarios what-if, estado modelos ML.
- **Fase 5.8** — Página de configuración: perfil + cuentas, categorías CRUD, configuración fiscal IRPF, preferencias UI.
- **Fase 6.1** — Infraestructura de producción: Nginx reverse proxy con SSL local (mkcert), backups automáticos de PostgreSQL (pg_dump + crond), health checks completos en todos los contenedores, `docker-compose.yml` de producción optimizado (sin bind mounts, workers múltiples, sin puertos expuestos directos), `frontend/Dockerfile.prod` con build multi-stage (adapter-node), documentación de despliegue en `Docs/DEPLOYMENT.md`.
- **Fase 6.2** — Calidad: coverage backend con umbral 80% (`backend/pyproject.toml`), ESLint + Prettier para frontend (`frontend/eslint.config.js`, `frontend/.prettierrc`), tests E2E con Playwright (`frontend/playwright.config.ts`, `frontend/tests/e2e/`), CI con GitHub Actions 3 jobs (backend, frontend, ml-service lint) en `.github/workflows/ci.yml`.
- **Fase 6.3** — Documentación: `README.md` completo con badges, características, quickstart, estructura del proyecto y links a docs; `CONTRIBUTING.md` con flujo fork/PR, estándares Ruff/ESLint, convención de commits y checklist pre-PR; `LICENSE` MIT; `Docs/ROADMAP.md` actualizado con fase 6.3 completada.

Los módulos `utils/` financieros (TIR, VAN) siguen sin implementar. Ver `Docs/ROADMAP.md` para el plan completo.

## Validación con tests

**Todo cambio debe ir acompañado de tests.** No se considera terminada ninguna implementación sin tests que la validen.

```bash
docker compose -f docker-compose.dev.yml exec backend pytest --cov=app -v
```

## Documentación

Con cada cambio significativo actualizar:

- `Docs/ARCHITECTURE.md` — si cambia el stack, modelos de datos, endpoints o estrategia ML
- `Docs/ROADMAP.md` — marcar fases completadas y ajustar las siguientes
- `CLAUDE.md` — si cambia la estructura de módulos, comandos o el estado de implementación

## Configuración

- Variables de entorno en `.env` (copiar desde `.env.example`). La clase `Settings` en `config.py` las carga automáticamente.
- Ruff con `line-length = 100`, target Python 3.12, reglas: E, F, I, N, W, UP, B, SIM.
- pytest con `asyncio_mode = "auto"`, tests en `backend/tests/`; coverage `fail_under = 80`.
- ESLint (flat config v9) + Prettier en `frontend/`; scripts: `npm run lint`, `npm run format:check`.
- Playwright E2E en `frontend/tests/e2e/`; script: `npm run test:e2e`.
- CI en `.github/workflows/ci.yml`: 3 jobs (backend tests+lint, frontend lint+test+e2e, ml-service lint).
- Documentación detallada en `Docs/ARCHITECTURE.md`; plan de desarrollo en `Docs/ROADMAP.md`.
