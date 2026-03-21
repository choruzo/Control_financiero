# FinControl - Arquitectura del Sistema

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

┌──────────────────────┐
│  tax_config          │
├──────────────────────┤
│ id (PK)              │
│ user_id (FK)         │
│ year                 │
│ irpf_brackets (JSONB)│  ←── [{min, max, rate}, ...]
│ ss_rate              │
│ deductions (JSONB)   │
│ created_at           │
└──────────────────────┘
```

## 4. Endpoints API (Diseño Inicial)

```
Auth:
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh
  GET    /api/v1/auth/me

Accounts:
  GET    /api/v1/accounts
  POST   /api/v1/accounts
  PUT    /api/v1/accounts/{id}
  DELETE /api/v1/accounts/{id}
  GET    /api/v1/accounts/{id}/balance-history

Transactions:
  GET    /api/v1/transactions               ?account_id=&category_id=&date_from=&date_to=&type=
  POST   /api/v1/transactions
  POST   /api/v1/transactions/bulk           ←── importación CSV
  PUT    /api/v1/transactions/{id}
  DELETE /api/v1/transactions/{id}
  GET    /api/v1/transactions/summary        ←── resumen por periodo
  PATCH  /api/v1/transactions/{id}/category  ←── recategorizar (feedback al modelo)

Categories:
  GET    /api/v1/categories
  POST   /api/v1/categories
  PUT    /api/v1/categories/{id}
  DELETE /api/v1/categories/{id}

Budgets:
  GET    /api/v1/budgets                     ?year=&month=
  POST   /api/v1/budgets
  PUT    /api/v1/budgets/{id}
  DELETE /api/v1/budgets/{id}
  GET    /api/v1/budgets/status              ←── % consumido por categoría

Investments:
  GET    /api/v1/investments
  POST   /api/v1/investments
  PUT    /api/v1/investments/{id}
  DELETE /api/v1/investments/{id}
  GET    /api/v1/investments/summary         ←── rendimiento total

Mortgage Simulator:
  POST   /api/v1/mortgage/simulate           ←── cálculo de cuotas
  POST   /api/v1/mortgage/affordability      ←── máxima hipoteca permitida
  POST   /api/v1/mortgage/compare            ←── comparar escenarios fijo vs variable
  GET    /api/v1/mortgage/simulations        ←── simulaciones guardadas
  POST   /api/v1/mortgage/simulations        ←── guardar simulación

Analytics / Dashboard:
  GET    /api/v1/analytics/overview          ←── KPIs principales
  GET    /api/v1/analytics/cashflow          ?period=monthly&months=12
  GET    /api/v1/analytics/expenses-by-cat   ?date_from=&date_to=
  GET    /api/v1/analytics/savings-rate      ?months=12
  GET    /api/v1/analytics/trends            ←── tendencias temporales

ML / Predictions:
  POST   /api/v1/ml/categorize               ←── categorizar transacción(es)
  GET    /api/v1/ml/predictions/cashflow     ?months_ahead=12
  POST   /api/v1/ml/scenarios/simulate       ←── "¿qué pasa si...?"
  GET    /api/v1/ml/models/status            ←── estado de los modelos
  POST   /api/v1/ml/models/retrain           ←── forzar reentrenamiento

Tax:
  GET    /api/v1/tax/config                  ?year=
  PUT    /api/v1/tax/config
  POST   /api/v1/tax/calculate-net           ←── bruto → neto con IRPF+SS
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

### 5.2 Predicción de Flujo de Caja (LSTM)

**Arquitectura:** LSTM bidireccional con attention
- **Input features:** Ingreso/gasto mensual, categoría, mes del año, indicadores macro (Euríbor)
- **Output:** Predicción de ingreso/gasto para los próximos N meses
- **Baseline:** Facebook Prophet (para comparar y como fallback)
- **Reentrenamiento:** Automático mensual via Celery Beat

### 5.3 Análisis de Escenarios

Motor basado en reglas + Monte Carlo:
- Modificar parámetros (sueldo ±X%, Euríbor, gastos)
- Aplicar tramos IRPF actualizados
- Simular N escenarios con variabilidad
- Devolver distribución de resultados (percentiles P10, P50, P90)

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
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── README.md
├── docs/
│   ├── ARCHITECTURE.md          ← este archivo
│   ├── API.md
│   └── DEVELOPMENT.md
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              ← FastAPI app
│   │   ├── config.py            ← Settings (pydantic-settings)
│   │   ├── database.py          ← Engine, session
│   │   ├── models/              ← SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── account.py
│   │   │   ├── transaction.py
│   │   │   ├── category.py
│   │   │   ├── budget.py
│   │   │   ├── investment.py
│   │   │   ├── mortgage.py
│   │   │   └── tax.py
│   │   ├── schemas/             ← Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── transaction.py
│   │   │   └── ...
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py          ← Dependencias (get_db, get_current_user)
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py    ← Router principal v1
│   │   │       ├── auth.py
│   │   │       ├── accounts.py
│   │   │       ├── transactions.py
│   │   │       ├── categories.py
│   │   │       ├── budgets.py
│   │   │       ├── investments.py
│   │   │       ├── mortgage.py
│   │   │       ├── analytics.py
│   │   │       ├── ml.py
│   │   │       └── tax.py
│   │   ├── services/            ← Lógica de negocio
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── transaction_service.py
│   │   │   ├── mortgage_service.py
│   │   │   ├── analytics_service.py
│   │   │   └── tax_service.py
│   │   ├── tasks/               ← Celery tasks
│   │   │   ├── __init__.py
│   │   │   └── ml_tasks.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── financial.py     ← Funciones financieras (TIR, VAN, amortización)
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_transactions.py
│       └── ...
│
├── ml-service/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              ← FastAPI app del servicio ML
│   │   ├── config.py
│   │   ├── models/
│   │   │   ├── categorizer.py   ← DistilBERT categorización
│   │   │   ├── forecaster.py    ← LSTM predicción
│   │   │   └── scenarios.py     ← Motor de escenarios
│   │   ├── training/
│   │   │   ├── train_categorizer.py
│   │   │   ├── train_forecaster.py
│   │   │   └── datasets.py
│   │   └── api/
│   │       ├── __init__.py
│   │       └── endpoints.py
│   ├── data/
│   │   └── pretrained/          ← Modelos pre-entrenados
│   └── tests/
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app.html
│   │   ├── app.css
│   │   ├── lib/
│   │   │   ├── api/             ← Cliente API
│   │   │   ├── components/      ← Componentes reutilizables
│   │   │   │   ├── charts/
│   │   │   │   ├── forms/
│   │   │   │   └── layout/
│   │   │   ├── stores/          ← Svelte stores
│   │   │   └── utils/
│   │   └── routes/
│   │       ├── +layout.svelte
│   │       ├── +page.svelte     ← Dashboard principal
│   │       ├── login/
│   │       ├── transactions/
│   │       ├── budgets/
│   │       ├── investments/
│   │       ├── mortgage/
│   │       ├── predictions/
│   │       └── settings/
│   └── static/
│
└── nginx/
    ├── nginx.conf
    └── Dockerfile
```
