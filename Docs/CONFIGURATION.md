---
title: FinControl - Configuración y Despliegue
aliases:
  - Configuración
  - Configuration
  - Deployment
  - Docker
tags:
  - fincontrol
  - configuracion
  - docker
  - despliegue
  - env
related:
  - "[[ARCHITECTURE]]"
  - "[[SERVICES]]"
  - "[[ML_SERVICE]]"
  - "[[FRONTEND]]"
  - "[[TESTING]]"
status: activo
created: 2026-03-22
updated: 2026-03-22
---

# FinControl - Configuración y Despliegue

> [!info] Documentación relacionada
> - [[ARCHITECTURE|Arquitectura del Sistema]] — Visión general y stack tecnológico
> - [[SERVICES|Capa de Servicios]] — Lógica de negocio que consume estas configuraciones
> - [[ML_SERVICE|Servicio ML]] — Configuración del microservicio de IA
> - [[FRONTEND|Frontend]] — Configuración del cliente SvelteKit
> - [[TESTING|Guía de Testing]] — Ejecutar tests en Docker y local

---

## 1. Inicio Rápido

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Levantar todos los servicios
docker compose -f docker-compose.dev.yml up --build

# 3. Verificar
curl http://localhost:8000/health     # Backend
curl http://localhost:8001/health     # ML Service
open http://localhost:3000            # Frontend
open http://localhost:8000/docs       # Swagger UI
```

> [!warning] Producción
> Cambiar **todas** las contraseñas y secretos antes de desplegar en producción:
> `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `SECRET_KEY`.

---

## 2. Variables de Entorno

Todas las variables se definen en `.env` (raíz del proyecto) y se cargan automáticamente por cada servicio.

### 2.1 Aplicación General

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `APP_NAME` | `str` | `FinControl` | Nombre de la aplicación |
| `APP_ENV` | `str` | `development` | Entorno: `development`, `production` |
| `DEBUG` | `bool` | `true` | Modo debug (logging detallado) |
| `SECRET_KEY` | `str` | — | Clave secreta general (no usada directamente; usar `JWT_SECRET_KEY`) |

### 2.2 Base de Datos (PostgreSQL)

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `POSTGRES_HOST` | `str` | `postgres` | Host del servidor PostgreSQL |
| `POSTGRES_PORT` | `int` | `5432` | Puerto PostgreSQL |
| `POSTGRES_DB` | `str` | `fincontrol` | Nombre de la base de datos |
| `POSTGRES_USER` | `str` | `fincontrol` | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | `str` | `changeme` | Contraseña PostgreSQL |

> [!tip] URL de conexión
> La URL se construye automáticamente en `config.py` como propiedad computada:
> ```
> postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}
> ```

### 2.3 Redis

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `REDIS_URL` | `str` | `redis://redis:6379/0` | URL de conexión a Redis (cache general) |

**Distribución de bases de datos Redis:**

| DB | Uso |
|---|---|
| `0` | Cache general del backend |
| `1` | Celery broker (cola de tareas) |
| `2` | Celery result backend (resultados) |
| `3` | ML Service (feedback categorizador) |

### 2.4 JWT (Autenticación)

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `JWT_SECRET_KEY` | `str` | `change-me-jwt-secret` | Clave para firmar tokens JWT (HS256) |
| `JWT_ALGORITHM` | `str` | `HS256` | Algoritmo de firma |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `30` | Expiración del access token (minutos) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `int` | `7` | Expiración del refresh token (días) |

> [!danger] Seguridad
> **Cambiar `JWT_SECRET_KEY`** en producción. La clave por defecto solo es aceptable en desarrollo.

### 2.5 ML Service (conexión desde Backend)

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `ML_SERVICE_URL` | `str` | `http://ml-service:8001` | URL interna del microservicio ML |
| `ML_CATEGORIZATION_THRESHOLD` | `float` | `0.85` | Umbral de confianza para auto-asignar categoría |
| `ML_SERVICE_PORT` | `int` | `8001` | Puerto expuesto del ML Service |

### 2.6 Celery (Tareas Programadas)

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `CELERY_BROKER_URL` | `str` | `redis://redis:6379/1` | URL del broker Celery |
| `CELERY_RESULT_BACKEND` | `str` | `redis://redis:6379/2` | URL del backend de resultados |

Campos adicionales en `config.py` (no en `.env.example`, con defaults):

| Campo | Default | Descripción |
|---|---|---|
| `ml_retrain_min_feedback` | `10` | Feedback mínimo para disparar reentrenamiento |
| `ml_retrain_schedule_hour` | `3` | Hora UTC del reentrenamiento semanal (3AM) |
| `ml_retrain_schedule_day_of_week` | `"0"` | Día del reentrenamiento (0 = domingo) |
| `ml_forecast_min_months` | `6` | Mínimo meses históricos para forecast |
| `ml_forecast_max_ahead` | `12` | Máximo meses a predecir |
| `ml_forecast_retrain_schedule_hour` | `4` | Hora del reentrenamiento mensual (4AM) |

### 2.7 Escenarios y AI Affordability

| Campo en `config.py` | Default | Descripción |
|---|---|---|
| `scenario_monte_carlo_simulations` | `1000` | Simulaciones Monte Carlo para escenarios |
| `ai_affordability_default_euribor` | `3.5` | Euríbor base si no hay simulación guardada |
| `ai_affordability_default_spread` | `0.8` | Spread base si no hay simulación guardada |
| `ai_affordability_monte_carlo_simulations` | `1000` | Simulaciones MC para AI affordability |

### 2.8 Frontend

| Variable | Tipo | Default | Descripción |
|---|---|---|---|
| `FRONTEND_PORT` | `int` | `3000` | Puerto expuesto del frontend |
| `VITE_API_URL` | `str` | `http://localhost:8000` | URL del backend accesible desde el **browser** (no desde Docker) |

> [!note] `VITE_API_URL`
> Esta variable se inyecta en el bundle del frontend vía Vite. Debe apuntar al backend desde la perspectiva del **navegador del usuario**, no desde la red Docker interna.

---

## 3. Configuración del ML Service

El ML Service tiene su propia clase `Settings` en `ml-service/app/config.py` con prefijo `ML_` para las variables de entorno.

| Variable (con prefijo `ML_`) | Tipo | Default | Descripción |
|---|---|---|---|
| `ML_APP_NAME` | `str` | `FinControl ML Service` | Nombre del servicio |
| `ML_APP_ENV` | `str` | `development` | Entorno |
| `ML_DEBUG` | `bool` | `true` | Modo debug |
| `ML_MODEL_PATH` | `str` | `/app/models` | Ruta base de modelos entrenados |
| `ML_DEVICE` | `str` | `cpu` | Dispositivo de inferencia (`cpu` / `cuda`) |
| `ML_CATEGORIZATION_THRESHOLD` | `float` | `0.92` | Confianza mínima para auto-asignar categoría |
| `ML_CATEGORIZATION_SUGGEST_THRESHOLD` | `float` | `0.5` | Confianza mínima para sugerir |
| `ML_REDIS_URL` | `str` | `redis://redis:6379/3` | Redis para almacenar feedback |
| `ML_MIN_FEEDBACK_FOR_RETRAIN` | `int` | `10` | Feedback mínimo para reentrenar |
| `ML_RETRAIN_EPOCHS` | `int` | `2` | Épocas de fine-tuning incremental |
| `ML_RETRAIN_BATCH_SIZE` | `int` | `16` | Batch size de reentrenamiento |
| `ML_FORECAST_MODEL_PATH` | `str` | `/app/models` | Ruta del modelo LSTM de forecasting |
| `ML_FORECAST_MIN_MONTHS` | `int` | `6` | Meses históricos mínimos |
| `ML_FORECAST_MAX_MONTHS_AHEAD` | `int` | `12` | Máximo meses a predecir |
| `ML_FORECAST_MIN_SERIES_FOR_RETRAIN` | `int` | `3` | Series mínimas para entrenar |
| `ML_FORECAST_RETRAIN_EPOCHS` | `int` | `20` | Épocas de entrenamiento LSTM |
| `ML_FORECAST_RETRAIN_BATCH_SIZE` | `int` | `16` | Batch size LSTM |

> [!info] Detalles de los modelos ML
> Ver [[ML_SERVICE#3. Modelos de IA|ML Service → Modelos de IA]] para la arquitectura completa de DistilBERT y LSTM.

---

## 4. Arquitectura Docker

### 4.1 Servicios

```
docker-compose.dev.yml
├── postgres        (PostgreSQL 16 Alpine)
├── redis           (Redis 7 Alpine)
├── backend         (Python 3.12 + FastAPI)
├── celery-worker   (Celery worker, 2 procesos)
├── celery-beat     (Celery Beat scheduler)
├── ml-service      (PyTorch 2.7 + CUDA 12.8)
└── frontend        (Node 20 Alpine + SvelteKit)
```

### 4.2 Puertos

| Servicio | Puerto Interno | Puerto Expuesto | Configurable |
|---|---|---|---|
| PostgreSQL | 5432 | 5432 | No |
| Redis | 6379 | 6379 | No |
| Backend API | 8000 | `${BACKEND_PORT:-8000}` | Sí |
| ML Service | 8001 | `${ML_SERVICE_PORT:-8001}` | Sí |
| Frontend | 3000 | `${FRONTEND_PORT:-3000}` | Sí |

### 4.3 Volúmenes

| Volumen | Tipo | Propósito |
|---|---|---|
| `postgres_data` | Named | Persistencia de datos PostgreSQL |
| `redis_data` | Named | Persistencia de datos Redis |
| `ml_models` | Named | Modelos ML entrenados (compartido entre containers) |
| `./backend/app` | Bind mount | Hot-reload del código backend |
| `./backend/tests` | Bind mount | Tests accesibles en el container |
| `./ml-service/app` | Bind mount | Hot-reload del código ML |
| `./ml-service/tests` | Bind mount | Tests ML accesibles |
| `./frontend/src` | Bind mount | HMR del código frontend |
| `./frontend/static` | Bind mount | Assets estáticos (HMR) |

### 4.4 Health Checks

| Servicio | Comando | Intervalo |
|---|---|---|
| PostgreSQL | `pg_isready -U fincontrol` | 10s |
| Redis | `redis-cli ping` | 10s |
| ML Service | `curl -f http://localhost:8001/health` | 30s |

### 4.5 Dependencias

```
backend       → postgres (healthy), redis (healthy)
celery-worker → postgres (healthy), redis (healthy)
celery-beat   → postgres (healthy), redis (healthy)
ml-service    → redis (healthy)
frontend      → (sin dependencias explícitas)
```

### 4.6 GPU (ML Service)

El ML Service solicita acceso GPU vía `deploy.resources.reservations`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

> [!tip] Sin GPU
> Si no hay GPU disponible, Docker Compose lanzará un warning pero el servicio arrancará con `device: cpu` (fallback automático).

---

## 5. Dockerfiles

### 5.1 Backend (`backend/Dockerfile`)

```dockerfile
FROM python:3.12-slim
# gcc + libpq-dev para compilar asyncpg
# Non-root user: appuser
# Expone puerto 8000
```

- **Base:** `python:3.12-slim`
- **Dependencias del sistema:** `gcc`, `libpq-dev` (para compilar `asyncpg`)
- **Instalación:** `pip install -e ".[dev]"` (instala dev deps)
- **Seguridad:** Usuario no-root `appuser`

### 5.2 ML Service (`ml-service/Dockerfile`)

```dockerfile
FROM pytorch/pytorch:2.7.0-cuda12.8-cudnn9-devel
# curl para health check
# Non-root user: appuser
# Expone puerto 8001
```

- **Base:** `pytorch/pytorch:2.7.0-cuda12.8-cudnn9-devel` (incluye PyTorch + CUDA)
- **Dependencias del sistema:** `curl` (para health check)
- **Seguridad:** Usuario no-root `appuser`

### 5.3 Frontend (`frontend/Dockerfile`)

```dockerfile
FROM node:20-alpine
# npm install en imagen (layer cacheada)
# Código fuente montado como volume → HMR
# Expone puerto 3000
```

- **Base:** `node:20-alpine`
- **Estrategia:** `node_modules` vive en la imagen (evita conflictos Linux/Windows); código fuente por bind mount

---

## 6. Desarrollo Local (Sin Docker)

### 6.1 Backend

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate       # Linux/Mac
# venv\Scripts\Activate.ps1    # Windows PowerShell

pip install -e ".[dev]"

# Requiere PostgreSQL y Redis locales
export POSTGRES_HOST=localhost
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/1
export CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Migraciones
alembic upgrade head

# Servidor
uvicorn app.main:app --reload --port 8000
```

### 6.2 ML Service

```bash
cd ml-service
python3.11 -m venv venv     # Python 3.11+ (imagen PyTorch)
source venv/bin/activate
pip install -e ".[dev]"

export ML_REDIS_URL=redis://localhost:6379/3
uvicorn app.main:app --reload --port 8001
```

### 6.3 Frontend

```bash
cd frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

---

## 7. Migraciones Alembic

```bash
# Generar nueva migración
docker compose -f docker-compose.dev.yml exec backend \
  alembic revision --autogenerate -m "descripcion_del_cambio"

# Aplicar migraciones pendientes
docker compose -f docker-compose.dev.yml exec backend \
  alembic upgrade head

# Revertir última migración
docker compose -f docker-compose.dev.yml exec backend \
  alembic downgrade -1

# Ver estado actual
docker compose -f docker-compose.dev.yml exec backend \
  alembic current
```

**Migraciones existentes:**

| Versión | Descripción |
|---|---|
| `0001` | Tablas `users` y `refresh_tokens` |
| `0002` | Tablas `accounts`, `categories`, `transactions` |
| `0003` | Tablas `budgets` y `budget_alerts` |
| `0004` | Tabla `investments` |
| `0005` | Tabla `mortgage_simulations` |
| `0006` | Tablas `tax_brackets` y `tax_configs` |

> [!info] Modelos detallados
> Ver [[DATA_MODELS|Modelos de Datos]] para la definición completa de cada tabla.

---

## 8. Lint y Formato (Ruff)

Configuración en `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]
ignore = ["B008"]  # Permite Depends() como default de argumento (patrón FastAPI)
```

```bash
# Verificar errores
docker compose -f docker-compose.dev.yml exec backend ruff check app/

# Corregir automáticamente
docker compose -f docker-compose.dev.yml exec backend ruff check --fix app/

# Formatear código
docker compose -f docker-compose.dev.yml exec backend ruff format app/
```

---

## 9. Celery Beat Schedule

El scheduler de Celery Beat ejecuta tareas programadas automáticamente:

| Tarea | Frecuencia | Hora | Descripción |
|---|---|---|---|
| `trigger_ml_retrain` | Semanal (domingo) | 3:00 AM | Reentrenamiento del categorizador DistilBERT |
| `trigger_forecast_retrain` | Mensual (día 1) | 4:00 AM | Reentrenamiento del LSTM de forecasting |

> [!info] Pipeline de reentrenamiento
> Ver [[ML_SERVICE#5. Pipeline de Reentrenamiento|ML Service → Pipeline de Reentrenamiento]] para detalles del proceso.

---

## 10. Dependencias del Proyecto

### Backend (`pyproject.toml`)

**Producción:**

| Paquete | Versión | Uso |
|---|---|---|
| `fastapi` | ≥0.115 | Framework web async |
| `uvicorn[standard]` | ≥0.32 | Servidor ASGI |
| `sqlalchemy[asyncio]` | ≥2.0.35 | ORM async |
| `asyncpg` | ≥0.30 | Driver PostgreSQL async |
| `alembic` | ≥1.14 | Migraciones de BD |
| `pydantic` | ≥2.10 | Validación de datos |
| `pydantic-settings` | ≥2.6 | Carga de configuración |
| `python-jose[cryptography]` | ≥3.3 | JWT |
| `bcrypt` | ≥4.0 | Hashing de contraseñas |
| `python-multipart` | ≥0.0.12 | OAuth2 form data |
| `celery[redis]` | ≥5.4 | Tareas asíncronas |
| `redis` | ≥5.2 | Cliente Redis |
| `httpx` | ≥0.28 | Cliente HTTP async (ML) |
| `numpy` | ≥2.1 | Cálculos numéricos |
| `scipy` | ≥1.14 | Newton-Raphson (TAE) |
| `structlog` | ≥24.4 | Logging estructurado |

**Desarrollo:**

| Paquete | Uso |
|---|---|
| `pytest` + `pytest-asyncio` | Tests async |
| `pytest-cov` + `coverage` | Cobertura |
| `aiosqlite` | SQLite async (tests) |
| `respx` | Mock de httpx (tests ML) |
| `ruff` | Linter + formatter |

### ML Service (`pyproject.toml`)

| Paquete | Versión | Uso |
|---|---|---|
| `fastapi` + `uvicorn` | — | Framework web |
| `transformers` | ≥4.46 | DistilBERT |
| `scikit-learn` | ≥1.4 | Métricas y preprocesamiento |
| `prophet` | ≥1.1 | Fallback de forecasting |
| `redis` | ≥5.2 | Almacén de feedback |
| `numpy` | ≥1.26 | Tensores y cálculos |
| PyTorch 2.7 | (imagen Docker) | LSTM e inferencia |

### Frontend (`package.json`)

| Paquete | Versión | Uso |
|---|---|---|
| `@skeletonlabs/skeleton` | ^2.10 | UI components |
| `@sveltejs/kit` | **2.12.1** (pinned) | Framework SvelteKit |
| `svelte` | ^4.2.19 | Svelte 4 (no 5) |
| `tailwindcss` | ^3.4 | CSS utility-first |
| `typescript` | ^5.5 | Type checking |
| `vitest` | ^2.1 | Test runner |

> [!warning] Versiones pinned
> `@sveltejs/kit` está pinado a `2.12.1` (sin `^`) para mantener compatibilidad con Skeleton UI v2 (Svelte 4). Versiones con `^` resuelven a Kit 2.55+ que requiere Svelte 5.