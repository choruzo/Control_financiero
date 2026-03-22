---
title: FinControl - Arquitectura del Sistema
aliases:
  - Arquitectura
  - Architecture
tags:
  - fincontrol
  - arquitectura
  - backend
  - frontend
  - ml
  - base-de-datos
related:
  - "[[ROADMAP]]"
status: activo
created: 2026-03-21
updated: 2026-03-21
---

# FinControl - Arquitectura del Sistema

> [!info] Documentación relacionada
> - [[ROADMAP|Roadmap de Desarrollo]] — Fases, tareas y progreso del proyecto

## 1. Visión General

**FinControl** es una aplicación personal de análisis financiero que permite gestionar ingresos, gastos, ahorro, inversiones, simulaciones hipotecarias y proyecciones financieras a largo plazo, con modelos de IA para categorización automática y predicción de ingresos/gastos futuros.

```
┌─────────────────────────────────────────────────────────────────┐
│                        DOCKER COMPOSE                          │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │   Frontend    │  │   Backend    │  │   ML Service          │ │
│  │   (Svelte)    │  │  (FastAPI)   │  │  (FastAPI + PyTorch)  │ │
│  │   Port 3000   │  │  Port 8000   │  │  Port 8001            │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
│         │                 │                       │             │
│         │          ┌──────┴───────┐               │             │
│         │          │              │               │             │
│  ┌──────▼──────┐  ┌▼────────────┐ ┌▼────────────┐             │
│  │   Nginx     │  │ PostgreSQL  │ │   Redis     │             │
│  │   Reverse   │  │  Port 5432  │ │  Port 6379  │             │
│  │   Proxy     │  │             │ │             │             │
│  │   Port 80   │  └─────────────┘ └─────────────┘             │
│  └─────────────┘                                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │   Celery Worker + Beat (tareas programadas)                ││
│  │   - Reentrenamiento de modelos                             ││
│  │   - Cálculo de métricas periódicas                         ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## 2. Stack Tecnológico

### Backend (Python 3.12+)
| Componente | Tecnología | Justificación |
|---|---|---|
| Framework Web | **FastAPI** | Async nativo, validación automática con Pydantic, OpenAPI docs auto-generada, excelente ecosistema ML |
| ORM | **SQLAlchemy 2.0 + Alembic** | ORM maduro, migraciones robustas, soporte async |
| Autenticación | **JWT (python-jose) + bcrypt** | Stateless, extensible a multi-usuario |
| Tareas async | **Celery + Redis** | Reentrenamiento de modelos en background, tareas programadas |
| Testing | **pytest + httpx** | Estándar de facto en Python |
| Validación | **Pydantic v2** | Integración nativa con FastAPI, rendimiento excelente |

### Frontend
| Componente | Tecnología | Justificación |
|---|---|---|
| Framework | **SvelteKit** | Bundle mínimo, rendimiento superior, curva de aprendizaje suave, reactividad nativa sin virtual DOM |
| Gráficos | **Apache ECharts** | El más completo para dashboards financieros (candlestick, heatmaps, gauges, drill-down) |
| UI Components | **Skeleton UI (Svelte)** | Componentes accesibles, tema oscuro/claro, bien integrado con Svelte |
| HTTP Client | **Fetch API nativo** | SvelteKit ya lo maneja bien |
| State | **Svelte Stores** | Reactivo nativo, sin dependencias extra |

### Base de Datos
| Componente | Tecnología | Justificación |
|---|---|---|
| Principal | **PostgreSQL 16** | ACID compliance (crucial para datos financieros), CTEs, window functions para análisis temporal, extensión `tablefunc` para pivots |
| Cache / Broker | **Redis 7** | Cache de cálculos, broker para Celery, sesiones |

### ML / IA
| Componente | Tecnología | Justificación |
|---|---|---|
| Categorización | **Transformer fine-tuned (DistilBERT español)** | Precisión superior en texto corto (conceptos bancarios), puede correr en tu RTX 3060Ti |
| Predicción temporal | **PyTorch LSTM + Facebook Prophet** | LSTM para patrones complejos, Prophet como baseline/comparación |
| Simulaciones | **NumPy + SciPy** | Cálculos hipotecarios, Monte Carlo para escenarios |
| Framework ML | **PyTorch 2.x** | Soporte CUDA nativo para tu 3060Ti, ecosistema rico |
| Serving | **FastAPI dedicado** | Microservicio separado para no bloquear el backend principal |

### Infraestructura
| Componente | Tecnología | Justificación |
|---|---|---|
| Contenedores | **Docker Compose** | Orquestación simple, ideal para single-server |
| Reverse Proxy | **Nginx** | Sirve frontend estático, proxy al backend, SSL local |
| Backups | **pg_dump + cron** | Backups automáticos de PostgreSQL |

## 3. Modelo de Datos (Esquema Conceptual)

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│    users     │     │   accounts       │     │  categories     │
├──────────────┤     ├──────────────────┤     ├─────────────────┤
│ id (PK)      │◄───┤ user_id (FK)     │     │ id (PK)         │
│ username     │     │ id (PK)          │     │ name            │
│ email        │     │ name             │     │ type (I/G)      │
│ password_hash│     │ type (checking/  │     │ parent_id (FK)  │
│ created_at   │     │   savings/       │     │ icon            │
│ settings     │     │   investment)    │     │ color           │
└──────────────┘     │ currency (EUR)   │     │ ml_keywords[]   │
                     │ initial_balance  │     └────────┬────────┘
                     └────────┬─────────┘              │
                              │                        │
                     ┌────────▼─────────┐              │
                     │  transactions    │              │
                     ├──────────────────┤              │
                     │ id (PK)          │              │
                     │ account_id (FK)  ├──────────────┘
                     │ category_id (FK) │
                     │ amount           │
                     │ type (income/    │
                     │   expense)       │
                     │ date             │
                     │ description      │
                     │ is_recurring     │
                     │ recurring_config │  ←── JSONB {period, day_of_month, end_date}
                     │ ml_categorized   │  ←── bool: categorizado por IA o manual
                     │ ml_confidence    │  ←── float: confianza del modelo
                     │ tags[]           │
                     │ created_at       │
                     └──────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   budgets        │     │  investments     │     │  mortgage_sims   │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ id (PK)          │     │ id (PK)          │     │ id (PK)          │
│ user_id (FK)     │     │ user_id (FK)     │     │ user_id (FK)     │
│ category_id (FK) │     │ account_id (FK)  │     │ name             │
│ amount_limit     │     │ type (deposit/   │     │ property_price   │
│ period (monthly/ │     │   fund/other)    │     │ down_payment     │
│   yearly)        │     │ principal        │     │ loan_amount      │
│ year             │     │ interest_rate    │     │ interest_rate    │
│ month            │     │ start_date       │     │ rate_type (fixed/│
│ alert_threshold  │     │ maturity_date    │     │   variable/mixed)│
│ created_at       │     │ current_value    │     │ euribor_spread   │
└──────────────────┘     │ auto_renew       │     │ term_years       │
                         │ notes            │     │ monthly_payment  │
                         └──────────────────┘     │ total_cost       │
                                                  │ amortization_tbl │ ←── JSONB
                                                  │ scenario_params  │ ←── JSONB
                                                  │ irpf_rate        │
                                                  │ created_at       │
                                                  └──────────────────┘

┌──────────────────┐     ┌──────────────────┐
│  ml_models       │     │  scenarios       │
├──────────────────┤     ├──────────────────┤
│ id (PK)          │     │ id (PK)          │
│ model_type       │     │ user_id (FK)     │
│ version          │     │ name             │
│ file_path        │     │ type             │
│ metrics (JSONB)  │     │ base_params      │ ←── JSONB
│ trained_at       │     │ modified_params  │ ←── JSONB
│ is_active        │     │ results (JSONB)  │
│ training_config  │     │ created_at       │
└──────────────────┘     └──────────────────┘
    (pendiente Fase 3.2)      (pendiente Fase 4.2)

┌──────────────────────┐     ┌──────────────────────┐
│  tax_brackets        │     │  tax_configs         │
├──────────────────────┤     ├──────────────────────┤
│ id (PK)              │     │ id (PK)              │
│ tax_year             │     │ user_id (FK)         │
│ bracket_type         │     │ tax_year             │
│   (general/ahorro)   │     │ gross_annual_salary  │
│ system               │     │ is_active            │
│ min_income           │     │ created_at           │
│ max_income           │     └──────────────────────┘
│ rate                 │     UniqueConstraint(user_id, tax_year)
└──────────────────────┘
  Seeded: 2025/2026
  (general + ahorro)
```

## 4. Endpoints API

> Los endpoints marcados con ✅ están implementados. Los marcados con 🔜 están planificados para fases futuras.

```
Auth: ✅
  POST   /api/v1/auth/register
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh
  GET    /api/v1/auth/me
  POST   /api/v1/auth/logout

Accounts: ✅
  GET    /api/v1/accounts
  POST   /api/v1/accounts
  GET    /api/v1/accounts/{id}
  PUT    /api/v1/accounts/{id}
  DELETE /api/v1/accounts/{id}

Transactions: ✅
  GET    /api/v1/transactions               ?account_id=&category_id=&date_from=&date_to=&type=&skip=&limit=
  POST   /api/v1/transactions
  GET    /api/v1/transactions/{id}
  PUT    /api/v1/transactions/{id}
  DELETE /api/v1/transactions/{id}
  POST   /api/v1/transactions/import/csv    ←── importación CSV (?account_id=&dry_run=)

Categories: ✅
  GET    /api/v1/categories
  POST   /api/v1/categories
  GET    /api/v1/categories/{id}
  PUT    /api/v1/categories/{id}
  DELETE /api/v1/categories/{id}

Budgets: ✅
  GET    /api/v1/budgets                     ?year=&month=
  POST   /api/v1/budgets
  GET    /api/v1/budgets/{id}
  GET    /api/v1/budgets/{id}/status         ←── % consumido del presupuesto
  PATCH  /api/v1/budgets/{id}
  DELETE /api/v1/budgets/{id}
  GET    /api/v1/budgets/status              ?period_year=&period_month=  ←── estado de todos los presupuestos
  GET    /api/v1/budgets/alerts
  PATCH  /api/v1/budgets/alerts/{id}/read

Investments: ✅
  GET    /api/v1/investments/summary         ←── rendimiento total agregado
  POST   /api/v1/investments
  GET    /api/v1/investments
  GET    /api/v1/investments/{id}
  GET    /api/v1/investments/{id}/status     ←── rendimiento acumulado a hoy
  PATCH  /api/v1/investments/{id}
  DELETE /api/v1/investments/{id}
  POST   /api/v1/investments/{id}/renew      ←── renovar depósito

Mortgage Simulator: ✅
  POST   /api/v1/mortgage/simulate           ←── cálculo de cuotas + tabla de amortización
  POST   /api/v1/mortgage/compare            ←── compara hasta 5 escenarios
  GET    /api/v1/mortgage/affordability      ?months=&tax_config_id=  ←── máxima hipoteca permitida
  POST   /api/v1/mortgage/simulations        ←── guardar simulación
  GET    /api/v1/mortgage/simulations
  GET    /api/v1/mortgage/simulations/{id}
  DELETE /api/v1/mortgage/simulations/{id}

Analytics: ✅
  GET    /api/v1/analytics/overview          ←── KPIs: ingresos/gastos/ahorro/balance
  GET    /api/v1/analytics/cashflow          ?months=
  GET    /api/v1/analytics/expenses-by-category  ?date_from=&date_to=
  GET    /api/v1/analytics/savings-rate      ?months=
  GET    /api/v1/analytics/trends            ←── cambio % vs mes anterior y vs media 12m

Tax: ✅
  GET    /api/v1/tax/brackets                ←── tramos IRPF seeded (2025/2026)
  POST   /api/v1/tax/configs
  GET    /api/v1/tax/configs
  GET    /api/v1/tax/configs/{id}
  GET    /api/v1/tax/configs/{id}/calculation  ←── bruto → neto con IRPF + SS
  PATCH  /api/v1/tax/configs/{id}
  DELETE /api/v1/tax/configs/{id}

ML (infraestructura, modelo pendiente Fase 3.2): ✅
  POST   /api/v1/ml/predict                  ←── predice categoría (stub hasta Fase 3.2)
  POST   /api/v1/ml/feedback                 ←── feedback usuario (almacenamiento pendiente Fase 3.3)
  GET    /api/v1/ml/status                   ←── estado del modelo

ML (endpoints pendientes Fase 4): 🔜
  GET    /api/v1/ml/predictions/cashflow     ?months_ahead=12
  POST   /api/v1/ml/scenarios/simulate       ←── "¿qué pasa si...?"
  POST   /api/v1/ml/models/retrain           ←── forzar reentrenamiento
```

## 5. Estrategia ML/IA

### 5.1 Categorización Automática de Transacciones

**Modelo:** DistilBERT multilingüe fine-tuned
- **Input:** Descripción de la transacción ("COMPRA MERCADONA 1234")
- **Output:** Categoría predicha + confianza
- **Umbral:** Si confianza > 0.85 → asignar automáticamente; si no → sugerir al usuario
- **Feedback loop:** Cuando el usuario corrige una categoría, se almacena para reentrenamiento
- **Entrenamiento inicial:** Dataset sintético + primeras 100-200 transacciones manuales
- **Hardware:** Inferencia en GPU (RTX 3060Ti), training también en GPU

```python
# Pseudocódigo del pipeline
class TransactionCategorizer:
    def predict(self, description: str) -> tuple[str, float]:
        tokens = self.tokenizer(description)
        logits = self.model(tokens)
        category = self.label_map[logits.argmax()]
        confidence = softmax(logits).max()
        return category, confidence

    def retrain(self, new_data: list[tuple[str, str]]):
        # Fine-tune incremental con datos corregidos por el usuario
        # Se ejecuta en Celery worker con acceso a GPU
        ...
```

### 5.2 Predicción de Flujo de Caja (LSTM) ✅ Fase 4.1

**Arquitectura:** `CashflowLSTM` — LSTM bidireccional (2 capas, hidden=64, dropout=0.2)
- **Input:** Secuencia de 12 meses de `[income, expenses]` normalizados con `StandardScaler`
- **Output:** Predicción del mes siguiente; rolling prediction para N meses hacia adelante
- **Intervalos de confianza:** MC Dropout (50 muestras) → P10/P50/P90
- **Fallback Prophet:** Si LSTM no está entrenado, usa Facebook Prophet como baseline estadístico
- **Modo degradado:** Si tampoco hay Prophet, devuelve ceros (sin interrumpir el flujo)
- **Reentrenamiento:** Automático mensual (1 de cada mes a las 4AM via Celery Beat)
- **Training data:** Series históricas reales almacenadas en Redis desde peticiones de forecast + dataset sintético

**Módulos implementados:**
- `ml-service/app/ml/lstm_model.py` — Arquitectura PyTorch (`CashflowLSTM`)
- `ml-service/app/ml/forecaster.py` — Singleton (patrón análogo a `ModelManager`)
- `ml-service/app/routers/forecast.py` — `POST /forecast`, `POST /forecast/retrain`, `GET /forecast/status`
- `ml-service/data/generate_timeseries.py` — Generador de dataset sintético (200 series × 36 meses)
- `ml-service/scripts/train_forecaster.py` — CLI de entrenamiento inicial

**Endpoints Backend:**
- `GET /analytics/forecast?months=6` — Predicción de cashflow con intervalos de confianza

### 5.3 Análisis de Escenarios

Motor basado en reglas + Monte Carlo:
- Modificar parámetros (sueldo ±X%, Euríbor, gastos)
- Aplicar tramos IRPF actualizados
- Simular N escenarios con variabilidad
- Devolver distribución de resultados (percentiles P10, P50, P90)

### 5.4 Microservicio ML (Fase 3.1 — infraestructura operativa)

El ml-service es un proceso FastAPI independiente que corre en el puerto 8001 dentro de Docker Compose, con acceso a GPU via `nvidia` runtime. Su API interna (consumida por el backend a través de `MLClient`) ya está desplegada en forma de stubs:

| Endpoint | Descripción | Estado |
|---|---|---|
| `GET /health` | Health check; indica si el modelo está cargado | ✅ stub |
| `POST /predict` | Recibe descripción → devuelve categoría + confianza | ✅ stub (Fase 3.2 añade modelo real) |
| `POST /feedback` | Recibe corrección del usuario para reentrenamiento | ✅ stub (Fase 3.3 añade persistencia) |
| `GET /model/status` | Versión, accuracy y fecha de último training | ✅ stub |

El backend consume estos endpoints a través de `MLClient` con **degradación graceful**: si el ml-service no está disponible, devuelve respuestas con `ml_available=False` sin interrumpir el flujo principal de la aplicación.

## 6. Seguridad

- **Autenticación:** JWT con refresh tokens, bcrypt para passwords
- **CORS:** Restringido a origen del frontend
- **Rate limiting:** En Nginx
- **Datos sensibles:** Nunca en logs, cifrado en reposo (PostgreSQL TDE opcional)
- **Docker:** Contenedores con usuario no-root, redes internas aisladas
- **Backups:** pg_dump diario automático con retención de 30 días

## 7. Estructura de Carpetas del Proyecto

```
Control_financiero/
├── docker-compose.dev.yml
├── .env.example
├── README.md
├── CLAUDE.md
├── Docs/
│   ├── ARCHITECTURE.md          ← este archivo
│   └── ROADMAP.md
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │       ├── 0001_create_users_and_refresh_tokens.py
│   │       ├── 0002_add_accounts_categories_transactions.py
│   │       ├── 0003_add_budgets.py
│   │       ├── 0004_add_investments.py
│   │       ├── 0005_add_mortgage_simulations.py
│   │       └── 0006_add_tax.py
│   ├── app/
│   │   ├── main.py              ← FastAPI app, CORS, lifespan (seeder categorías + tramos IRPF)
│   │   ├── config.py            ← Settings (pydantic-settings), property database_url
│   │   ├── database.py          ← Engine SQLAlchemy async, get_db dependency
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── refresh_token.py
│   │   │   ├── account.py
│   │   │   ├── transaction.py
│   │   │   ├── category.py
│   │   │   ├── budget.py        ← Budget + BudgetAlert
│   │   │   ├── investment.py
│   │   │   ├── mortgage.py      ← MortgageSimulation
│   │   │   └── tax.py           ← TaxBracket + TaxConfig
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── accounts.py
│   │   │   ├── transactions.py
│   │   │   ├── categories.py
│   │   │   ├── imports.py       ← ImportResult, ImportRowResult
│   │   │   ├── budgets.py
│   │   │   ├── investments.py
│   │   │   ├── mortgage.py
│   │   │   ├── analytics.py
│   │   │   ├── ml.py            ← MLPredictRequest/Response, MLFeedbackRequest/Response
│   │   │   └── tax.py
│   │   ├── api/
│   │   │   ├── deps.py          ← get_db, get_current_user
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── accounts.py
│   │   │       ├── transactions.py
│   │   │       ├── categories.py
│   │   │       ├── budgets.py
│   │   │       ├── investments.py
│   │   │       ├── mortgage.py
│   │   │       ├── analytics.py
│   │   │       ├── ml.py        ← proxy al ml-service con degradación graceful
│   │   │       └── tax.py
│   │   ├── services/
│   │   │   ├── auth.py
│   │   │   ├── accounts.py
│   │   │   ├── transactions.py
│   │   │   ├── categories.py    ← incluye seeder de categorías por defecto
│   │   │   ├── imports.py       ← lógica de importación CSV con deduplicación
│   │   │   ├── budgets.py
│   │   │   ├── investments.py
│   │   │   ├── mortgage.py
│   │   │   ├── analytics.py
│   │   │   ├── ml_client.py     ← MLClient: HTTP async con degradación graceful
│   │   │   └── tax.py           ← incluye seeder de tramos IRPF
│   │   ├── tasks/               ← Celery tasks (pendiente Fase 3.3)
│   │   │   └── __init__.py
│   │   └── utils/
│   │       ├── csv_parser.py    ← Parser CSV OpenBank (sep `;`, fecha DD/MM/YYYY)
│   │       ├── mortgage.py      ← Cálculos: PMT, amortización, TAE, closing_costs
│   │       └── logging.py       ← Logging estructurado (structlog)
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/
│       │   └── openbank_sample.csv
│       ├── test_auth.py
│       ├── test_accounts.py
│       ├── test_transactions.py
│       ├── test_imports.py
│       ├── test_categories.py
│       ├── test_budgets.py
│       ├── test_investments.py
│       ├── test_mortgage.py
│       ├── test_analytics.py
│       ├── test_ml_client.py
│       └── test_tax.py
│
├── ml-service/
│   ├── Dockerfile               ← pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime, usuario no-root
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py              ← FastAPI, middleware logging, lifespan (placeholder modelo)
│   │   ├── config.py            ← model_path, thresholds (0.85/0.5), redis_url
│   │   ├── routers/
│   │   │   ├── health.py        ← GET /health
│   │   │   ├── predict.py       ← POST /predict  (stub Fase 3.1, real en Fase 3.2)
│   │   │   ├── feedback.py      ← POST /feedback (stub Fase 3.1, persiste en Fase 3.3)
│   │   │   └── model.py         ← GET /model/status
│   │   └── schemas/
│   │       ├── predict.py       ← PredictRequest, PredictResponse
│   │       ├── feedback.py      ← FeedbackRequest, FeedbackResponse
│   │       └── model.py         ← ModelStatusResponse
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       └── test_predict.py
│
└── frontend/                    ← Pendiente Fase 5
    └── (por implementar)
```
