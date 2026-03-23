---
title: FinControl - Guía de Testing
aliases:
  - Testing
  - Tests
  - Guía de Tests
tags:
  - fincontrol
  - testing
  - pytest
  - vitest
  - backend
  - frontend
  - ml
related:
  - "[[ARCHITECTURE]]"
  - "[[CONFIGURATION]]"
  - "[[API_REFERENCE]]"
  - "[[SERVICES]]"
  - "[[ML_SERVICE]]"
  - "[[FRONTEND]]"
status: activo
created: 2026-03-22
updated: 2026-03-22
---

# FinControl - Guía de Testing

> [!info] Documentación relacionada
> - [[CONFIGURATION|Configuración y Despliegue]] — Docker y variables de entorno
> - [[API_REFERENCE|Referencia de API]] — Endpoints que validan estos tests
> - [[SERVICES|Capa de Servicios]] — Lógica de negocio bajo test
> - [[ML_SERVICE|Servicio ML]] — Tests del microservicio de IA
> - [[FRONTEND|Frontend]] — Tests del cliente SvelteKit

---

## 1. Resumen

| Servicio | Archivos | Tests | Framework | Entorno |
|---|---|---|---|---|
| **Backend** | 14 | 228 | pytest + pytest-asyncio | SQLite in-memory |
| **ML Service** | 6 | 68 | pytest + pytest-asyncio | Degraded mode |
| **Frontend** | 10 | 83 | Vitest + jsdom | vi.mock SvelteKit |
| **Total** | **30** | **379** | — | — |

---

## 2. Ejecutar Tests

### 2.1 Con Docker (recomendado)

```bash
# ── Backend ──
# Todos
docker compose -f docker-compose.dev.yml exec backend pytest -v

# Con cobertura
docker compose -f docker-compose.dev.yml exec backend pytest --cov=app -v

# Archivo específico
docker compose -f docker-compose.dev.yml exec backend pytest tests/test_auth.py -v

# Test individual
docker compose -f docker-compose.dev.yml exec backend pytest tests/test_auth.py::test_login_success -v

# ── ML Service ──
docker compose -f docker-compose.dev.yml exec ml-service pytest -v

# ── Frontend ──
docker compose -f docker-compose.dev.yml exec frontend npm run test
docker compose -f docker-compose.dev.yml exec frontend npm run test:coverage
```

### 2.2 Sin Docker (local)

```bash
# Backend
cd backend && source venv/bin/activate
pytest -v

# ML Service
cd ml-service && source venv/bin/activate
pytest -v

# Frontend
cd frontend
npm run test
```

---

## 3. Infraestructura de Tests

### 3.1 Backend — `conftest.py`

La fixture principal `client` proporciona un `AsyncClient` respaldado por una BD SQLite in-memory:

```python
@pytest.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    # Crea todas las tablas, seedea categorías y tramos IRPF
    # Override de get_db → sesión aislada por test
    # Cleanup automático al terminar
```

**Características:**
- **Aislamiento total:** Cada test tiene su propia BD (in-memory, `StaticPool`)
- **Seeders automáticos:** Categorías default + tramos fiscales IRPF se insertan antes de cada test
- **Sin PostgreSQL:** Usa `aiosqlite` para evitar dependencias externas
- **Transporte:** `httpx.ASGITransport` (tests directos contra la app FastAPI, sin red)

### 3.2 ML Service — `conftest.py`

```python
@pytest.fixture(autouse=True, scope="session")
async def setup_model_manager():
    # ModelManager en modo degradado (sin modelo en disco)
    # Forecaster en modo degradado
    # app.state.retrain_in_progress = False
```

**Características:**
- **Scope `session`:** Se inicializa una vez para todos los tests
- **Modo degradado:** `ModelManager` y `Forecaster` se cargan sin modelo real → devuelven resultados stub
- **Sin GPU:** Siempre `device="cpu"` en tests

### 3.3 Frontend — `setup.ts`

```typescript
import '@testing-library/jest-dom';   // Matchers DOM
vi.mock('$app/environment', () => ({ browser: true }));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$app/stores', () => { /* page store mock */ });
```

**Configuración Vitest** (`vite.config.ts`):
- **Entorno:** `jsdom`
- **Globals:** `true` (describe/it/expect sin importar)
- **Setup:** `./tests/setup.ts`
- **Cobertura:** `v8` sobre `src/**/*.{ts,svelte}`

---

## 4. Patrones de Testing

### 4.1 Helpers de Autenticación

Casi todos los tests de backend necesitan un usuario autenticado. El patrón es:

```python
async def _register_and_token(client) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "testpass123"
    })
    resp = await client.post("/api/v1/auth/login",
        data={"username": "user@test.com", "password": "testpass123"})
    return resp.json()["access_token"]
```

### 4.2 Mock de ML Service con `respx`

Para tests que involucran llamadas al servicio ML, se usa `respx` para interceptar `httpx`:

```python
@respx.mock
async def test_ml_auto_assigns_category(client):
    respx.post("http://ml-service:8001/predict").mock(
        return_value=httpx.Response(200, json={
            "predicted_category": "Alimentación",
            "confidence": 0.95, ...
        })
    )
    # La transacción creada tendrá category auto-asignada
```

### 4.3 Degradación Graceful

Todos los tests de integración ML verifican que el sistema sigue funcionando cuando el servicio ML no está disponible:

```python
async def test_ml_unavailable_does_not_fail(client):
    respx.post("http://ml-service:8001/predict").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )
    # La respuesta sigue siendo 200, sin categoría ML
```

### 4.4 Aislamiento de Usuarios

Los tests verifican que un usuario no puede acceder a datos de otro:

```python
async def test_get_account_other_user(client):
    token_a = await _register_and_token(client, "a@test.com")
    token_b = await _register_and_token(client, "b@test.com")
    acct = await _create_account(client, token_a)
    # User B obtiene 404, no 403 (no revela existencia)
    resp = await client.get(f"/api/v1/accounts/{acct['id']}",
        headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404
```

### 4.5 Precisión Financiera con `pytest.approx`

Para cálculos financieros (impuestos, hipotecas, intereses):

```python
assert result["net_monthly"] == pytest.approx(expected, rel=0.01)
```

### 4.6 Mock de Celery Tasks

Los tests de Celery usan `unittest.mock.patch` sobre el cliente HTTP síncrono:

```python
@patch("app.services.ml_client.httpx.Client")
def test_celery_task_calls_ml_client(mock_client_cls):
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.post.return_value = MagicMock(status_code=202, json=lambda: {...})
    mock_client_cls.return_value = mock_client
    trigger_ml_retrain()
```

### 4.7 Frontend — Mock de Fetch

```typescript
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);
// Configurar respuestas
mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(data) });
```

### 4.8 Frontend — Componentes Svelte

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
render(LoginPage);
await fireEvent.click(screen.getByLabelText('Login'));
await waitFor(() => expect(screen.getByText('Error')).toBeInTheDocument());
```

---

## 5. Catálogo de Tests

### 5.1 Backend (14 archivos, 228 tests)

#### `test_auth.py` — 16 tests
Autenticación JWT: registro, login (OAuth2 FormData), `/me`, refresh token rotation, rechazo de token incorrecto.

#### `test_accounts.py` — 13 tests
CRUD de cuentas bancarias. Aislamiento multi-usuario. Cascade delete de transacciones al eliminar cuenta.

#### `test_categories.py` — 11 tests
CRUD de categorías. Protección de categorías del sistema (403 en update/delete). Subcategorías jerárquicas. Idempotencia del seeder.

#### `test_transactions.py` — 20 tests
CRUD de transacciones. Paginación y filtros (fecha, tipo, cuenta, monto). Integración ML: auto-asignación, sugerencia, campos ML en respuesta, skip cuando hay categoría explícita.

#### `test_imports.py` — 11 tests
Importación CSV: success, dry_run, deduplicación, filas malformadas, archivo vacío, detección income/expense, aislamiento multi-usuario. Upload multipart.

#### `test_budgets.py` — 18 tests
CRUD de presupuestos. Estado de consumo (% gastado). Alertas automáticas al superar umbral. Deduplicación de alertas. Marcar alerta como leída.

#### `test_investments.py` — 23 tests
CRUD de inversiones. Interés simple y compuesto. Renovación. Resumen agregado. Validación Pydantic (`@model_validator`): compound requiere frequency, maturity > start.

#### `test_analytics.py` — 21 tests
Overview (ingresos/gastos/ahorro). Cashflow mensual. Gastos por categoría (con "Sin categoría"). Tasa de ahorro con medias móviles (3m, 6m). Tendencias (% cambio vs mes anterior y media 12m).

#### `test_tax.py` — 26 tests
Tramos IRPF (2025/2026, general/ahorro). CRUD de TaxConfig. Cálculo: SS 6.35%/6.50%, reducción trabajo, mínimo personal, tramos progresivos. Invariante: mayor salario → mayor tipo efectivo. Integración mortgages.

#### `test_mortgage.py` — 44 tests
Simulación hipotecaria (fijo/variable/mixto). Cuadro de amortización. Costes de cierre. Comparación de escenarios. Affordability (regla 35%). CRUD de simulaciones guardadas. **AI Affordability** (18 tests): forecast ML, stress tests Euríbor, invariantes P10≤P50≤P90, degradación ML.

#### `test_ml_client.py` — 15 tests
`MLClient` async: predict, feedback, status, health check. Router `/api/v1/ml`. Degradación graceful (siempre 200, nunca 500).

#### `test_celery_tasks.py` — 8 tests
Task `trigger_ml_retrain`. `MLClient.trigger_retrain_sync` (sync para Celery). Estados: started, skipped, in_progress, error.

#### `test_forecasting.py` — 11 tests
Endpoint `GET /analytics/forecast`. Validación de `months`. Degradación ML (ConnectError, Timeout). Task Celery `trigger_forecast_retrain`.

#### `test_scenarios.py` — 19 tests
`POST /scenarios/analyze`. Variaciones sueldo, gastos recurrentes, impacto fiscal, Euríbor sin hipoteca. Monte Carlo: intervalos P10≤P50≤P90, funciones puras `simulate_net_distribution`, `apply_scenario_modifications`.

### 5.2 ML Service (6 archivos, 68 tests)

#### `test_health.py` — 3 tests
`GET /health` y `GET /model/status` en modo degradado.

#### `test_predict.py` — 9 tests
`POST /predict` (degraded, validación). `POST /feedback` (almacenamiento, IDs únicos).

#### `test_categorization.py` — 18 tests
Catálogo de categorías (10 etiquetas). Preprocessor de texto bancario (normalización, prefijos, fechas, referencias). `ModelManager` degradado.

#### `test_forecast.py` — 15 tests
`POST /forecast` (degraded, validación, schema). `GET /forecast/status`. `POST /forecast/retrain`. Forecaster unit tests (rollover de año, cálculo neto).

#### `test_retrain.py` — 12 tests
`POST /retrain`: bloqueo concurrente, feedback insuficiente, Redis error. Callback `_on_retrain_complete`: modelo promovido (accuracy ≥ active−2%), rechazado, flag reset.

#### `test_trainer.py` — 11 tests
Funciones puras del trainer: versionado (`get_next_version`), `build_training_examples` (base + feedback), `train_val_split`. Edge cases: versión inválida, categoría fuera de rango, descripción vacía.

### 5.3 Frontend (10 archivos, 83 tests)

#### `api-client.test.ts` — 11 tests
`apiFetch`: token management, Bearer header injection, Content-Type. **Interceptor 401:** refresh + retry + mutex (previene refresh duplicado con 2 peticiones 401 concurrentes).

#### `auth-store.test.ts` — 7 tests
Store `authStore`: `setSession`, `logout`, `loadUser`. Derivados `isAuthenticated` y `currentUser`.

#### `analytics-api.test.ts` — 8 tests
Funciones de API del dashboard: URLs construidas correctamente, query params, valor devuelto.

#### `dashboard-store.test.ts` — 8 tests
Store del dashboard: carga paralela (Promise.allSettled), degradación graceful, cache 60s, `refresh()`, `markAlertRead()` optimista.

#### `format.test.ts` — 9 tests
Helpers de formateo: `formatCurrency` (es-ES EUR), `formatPercent`, `formatMonth`.

#### `kpi-card.test.ts` — 6 tests
Componente KpiCard: render del label, formateo por tipo, skeleton loader, indicador de tendencia.

#### `transactions-api.test.ts` — 9 tests
Funciones de API de transacciones: `getTransactions` (con/sin filtros), `createTransaction`, `updateTransaction`, `deleteTransaction`, `importCsv` (dry_run true/false), `sendMlFeedback`.

#### `transactions-store.test.ts` — 9 tests
Store de transacciones: carga paralela (tx+accounts+categories), `setFilters` (reset a página 1), `changePage`, `deleteTransaction`, `updateCategory` (con y sin feedback ML), cache 60s, `refresh()`.

#### `transaction-row.test.ts` — 8 tests
Componente TransactionRow: badge "🤖 IA" (confidence > 0.92), badge "💡 Sugerida" (0.5–0.92), sin badge (manual), colores de importe (verde/rojo/gris), nombre de cuenta y categoría, descripción.

#### `login-page.test.ts` — 7 tests
Página de login: tabs login/registro, formulario, error display, redirect a `/dashboard`, validación contraseña (mismatch, longitud mínima 8).

---

## 6. Cobertura

### Ejecutar con cobertura

```bash
# Backend
docker compose -f docker-compose.dev.yml exec backend \
  pytest --cov=app --cov-report=term-missing -v

# Frontend
docker compose -f docker-compose.dev.yml exec frontend \
  npm run test:coverage
```

### Áreas cubiertas

| Área | Cobertura |
|---|---|
| Auth (registro, login, JWT, refresh) | Alta |
| CRUD (accounts, categories, transactions, budgets, investments) | Alta |
| Importación CSV (deduplicación, validación) | Alta |
| Analytics (overview, cashflow, expenses, savings, trends) | Alta |
| Tax (IRPF, SS, cálculo neto) | Alta |
| Mortgage (simulación, comparación, affordability, AI) | Alta |
| ML integration (predict, feedback, degradación) | Alta |
| Celery tasks (retrain, forecast) | Media |
| Frontend stores y API client | Alta |
| Frontend páginas (login) | Media |

---

## 7. Convenciones de Testing

> [!important] Regla del proyecto
> **Todo cambio o implementación debe ir acompañado de tests.** No se considera terminada ninguna implementación si no tiene tests que la validen.

1. **Nombrar tests descriptivamente:** `test_<acción>_<condición>_<resultado_esperado>`
2. **Un assert principal por test** (helpers pueden tener asserts auxiliares)
3. **No depender de estado entre tests** — cada test es independiente
4. **Mockear servicios externos** (ML Service → `respx`, Celery → `unittest.mock`)
5. **Nunca mockear la BD** — usar SQLite in-memory para tests reales
6. **Verificar degradación graceful** — el sistema nunca retorna 500 por un servicio externo caído
7. **Verificar aislamiento de usuarios** — user B nunca ve datos de user A (retorna 404, no 403)
8. **Usar `pytest.approx`** para comparaciones financieras con decimales
