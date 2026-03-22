---
title: FinControl - Capa de Servicios
aliases:
  - Services
  - Business Logic
  - Lógica de Negocio
tags:
  - fincontrol
  - servicios
  - backend
  - logica-negocio
related:
  - "[[ARCHITECTURE]]"
  - "[[API_REFERENCE]]"
  - "[[DATA_MODELS]]"
  - "[[ML_SERVICE]]"
  - "[[CONFIGURATION]]"
  - "[[TESTING]]"
status: activo
created: 2026-03-22
updated: 2026-03-22
---

# FinControl - Capa de Servicios

> [!info] Documentación relacionada
> - [[ARCHITECTURE|Arquitectura]] — Flujo de una request y capas del sistema
> - [[API_REFERENCE|Referencia de API]] — Endpoints que invocan estos servicios
> - [[DATA_MODELS|Modelos de Datos]] — Modelos SQLAlchemy que los servicios manipulan
> - [[ML_SERVICE|Servicio ML]] — Microservicio invocado por `MLClient`
> - [[TESTING|Guía de Testing]] — Tests de integración de cada servicio

---

## Visión General

La capa de servicios (`backend/app/services/`) contiene **toda la lógica de negocio** de FinControl, desacoplada de los endpoints HTTP y de la base de datos. Cada router de la [[API_REFERENCE|API]] delega en un servicio correspondiente.

**Patrón de diseño:**
```
Router (validación HTTP) → Service (lógica) → SQLAlchemy (persistencia)
         ↓                      ↓                      ↓
   Pydantic schemas      Reglas de negocio       Queries async
```

**Convenciones:**
- Todas las funciones reciben `db: AsyncSession` como primer parámetro
- Validación de propiedad: siempre filtran por `user_id` para evitar acceso cruzado
- Errores devueltos como `HTTPException` (404, 409, etc.)
- Operaciones de BD son atómicas (auto-commit en `get_db` dependency)

---

## Autenticación (`services/auth.py`)

> Gestiona registro, login, JWT y refresh tokens. Ver [[API_REFERENCE#1. Autenticación (`/auth`)|endpoints de auth]] y [[DATA_MODELS#User|modelo User]].

### Funciones

#### `create_user(db, email, password) → User`
- Verifica unicidad del email
- Hash con bcrypt (12 rounds)
- Inserta `User` + emite tokens via `issue_tokens()`

#### `authenticate_user(db, email, password) → User`
- Busca por email
- **Comparación en tiempo constante** aunque el usuario no exista (mitigación de timing attacks)
- Devuelve `None` si falla (el router lanza 401)

#### `issue_tokens(db, user) → Token`
1. Crea access token JWT (HS256, expira en 30 min)
2. Genera refresh token con `jti` único (UUID)
3. Almacena `RefreshToken` en BD (expira en 7 días)
4. Retorna `{access_token, refresh_token, token_type: "bearer"}`

#### `rotate_refresh_token(db, refresh_jwt) → Token`
1. Decodifica JWT del refresh token
2. Busca `RefreshToken` por `jti` en BD
3. Verifica que no esté revocado ni expirado
4. Marca el token actual como `revoked=True`
5. Emite nuevo par de tokens

**Payload del JWT:**
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "exp": 1711234567,
  "jti": "unique-token-id"  // solo en refresh tokens
}
```

---

## Cuentas (`services/accounts.py`)

> CRUD de cuentas bancarias. Ver [[DATA_MODELS#Account|modelo Account]].

### Funciones

| Función | Descripción |
|---------|-------------|
| `create_account(db, user_id, data)` | Crea cuenta con datos del schema |
| `get_accounts(db, user_id)` | Lista todas las cuentas del usuario |
| `get_account(db, user_id, account_id)` | Obtiene una cuenta (404 si no es del usuario) |
| `update_account(db, user_id, account_id, data)` | Actualización parcial |
| `delete_account(db, user_id, account_id)` | Elimina (cascada → transacciones) |

**Seguridad:** Todas las funciones filtran por `user_id` para garantizar aislamiento multi-usuario.

---

## Categorías (`services/categories.py`)

> Gestión de categorías + seeder de categorías de sistema. Ver [[DATA_MODELS#Category|modelo Category]].

### `seed_default_categories(db) → None`

Ejecutado automáticamente en el `lifespan` de FastAPI. Crea categorías de sistema si no existen (idempotente).

**12 categorías raíz** con colores e iconos:
```python
DEFAULTS = [
    {"name": "Alimentación", "icon": "🛒", "color": "#4CAF50",
     "children": ["Supermercado", "Restaurantes"]},
    {"name": "Transporte", "icon": "🚗", "color": "#2196F3",
     "children": ["Combustible", "Transporte público", "Parking"]},
    # ... 10 más
]
```

**Verificación de idempotencia:** Busca por `name` + `is_system=True`. Si existe, no duplica.

### CRUD

| Función | Notas |
|---------|-------|
| `create_category(db, user_id, data)` | Crea categoría personalizada (user_id set) |
| `get_categories(db, user_id)` | Devuelve sistema (`user_id=NULL`) + personalizadas |
| `update_category(db, user_id, category_id, data)` | **Bloquea** si `is_system=True` |
| `delete_category(db, user_id, category_id)` | **Bloquea** si `is_system=True` |

---

## Transacciones (`services/transactions.py`)

> CRUD de transacciones con integración ML. Ver [[DATA_MODELS#Transaction|modelo Transaction]] y [[ML_SERVICE|servicio ML]].

### `create_transaction_with_ml(db, user_id, data) → TransactionResponse`

Flujo principal de creación con categorización automática:

```
┌─────────────┐    ¿category_id      ┌──────────────┐
│ POST /trans │───proporcionado?──Yes─►│ Crear sin ML │
└──────┬──────┘                       └──────────────┘
       │ No
       ▼
┌──────────────┐    ml_available?     ┌──────────────┐
│ ml.predict() │───────No────────────►│ Crear sin cat│
└──────┬───────┘                      └──────────────┘
       │ Sí
       ▼
┌──────────────────────────┐
│ Evaluar confianza        │
│ ≥ 0.92 → auto-asignar   │
│ ≥ 0.50 → sugerir        │
│ < 0.50 → sin categoría  │
└──────────────────────────┘
```

**Campos ML en la respuesta** (no persistidos en BD):
- `ml_suggested_category_id`: UUID de la categoría sugerida
- `ml_confidence`: confianza del modelo (0.0 - 1.0)

### `create_transaction(db, user_id, data) → Transaction`
Creación básica sin ML (usada internamente por importación CSV).

### `get_transactions(db, user_id, filters, skip, limit) → (List, total)`
Query con filtros combinables:
- `date_from` / `date_to` → rango de fechas
- `account_id` / `category_id` → filtro exacto
- `type` → `income` / `expense` / `transfer`
- Ordenamiento: `date DESC`
- Paginación: `skip` + `limit`

---

## Importación CSV (`services/imports.py`)

> Parser y lógica de importación para formato OpenBank. Ver [[API_REFERENCE#`POST /api/v1/transactions/import/csv`|endpoint de importación]].

### `import_transactions_from_csv(db, user_id, account_id, file_content, dry_run) → ImportResult`

**Pipeline:**
1. **Decodificación:** UTF-8 → fallback latin-1
2. **Parsing:** Delimitador `;`, formato OpenBank
3. **Por cada fila:**
   - Parsear fecha (`DD/MM/YYYY`), importe (coma decimal), concepto
   - **Deduplicar:** `SELECT` por `(date, amount, description, account_id)`
   - Si `dry_run=True` → validar sin insertar
   - Si duplicado → `skipped_duplicate`
   - Si error de formato → `error` con detalle
   - Si OK → INSERT + `imported`
4. **Resultado:** Contadores + detalle por fila

**Formato CSV esperado:**
```
Fecha;Concepto;Importe;Saldo
22/03/2026;COMPRA MERCADONA 1234;-45,50;1.454,50
```

**Parser de importes** (`utils/csv_parser.py`):
- `"−1.234,56"` → `Decimal("-1234.56")`
- Elimina separadores de miles (`.`), convierte coma decimal (`,` → `.`), maneja signo Unicode `−`

---

## Presupuestos (`services/budgets.py`)

> CRUD + cálculo de estado + alertas automáticas. Ver [[DATA_MODELS#Budget|modelo Budget]].

### `get_budget_status(db, user_id, budget_id) → BudgetStatusResponse`

Calcula el estado actual de un presupuesto:

1. Carga el presupuesto con su categoría
2. Suma gastos del período: `SELECT SUM(ABS(amount)) FROM transactions WHERE category_id = X AND date BETWEEN inicio_mes AND fin_mes AND amount < 0`
3. Calcula:
   - `remaining = limit_amount - spent_amount`
   - `percentage_used = (spent / limit) × 100`
   - `is_over_limit = spent > limit`
4. **Auto-alerta:** Si `percentage_used >= alert_threshold` y no hay alerta previa → crea `BudgetAlert`

### `list_budget_statuses(db, user_id, year, month) → List[BudgetStatusResponse]`
Calcula el estado de todos los presupuestos del período.

### Alertas

| Función | Descripción |
|---------|-------------|
| `list_alerts(db, user_id, unread_only?)` | Lista alertas, opcionalmente solo no leídas |
| `mark_alert_read(db, user_id, alert_id)` | Marca como leída (verifica propiedad via budget→user) |

---

## Inversiones (`services/investments.py`)

> CRUD + cálculo de rendimiento + renovación. Ver [[DATA_MODELS#Investment|modelo Investment]].

### `_calculate_return(principal, annual_rate_pct, days, interest_type, compounding_frequency) → Decimal`

Función interna de cálculo de rendimiento:

**Interés simple:**
$$I = P \times \frac{r}{100} \times \frac{d}{365}$$

**Interés compuesto:**
$$I = P \times \left(1 + \frac{r/100}{n}\right)^{n \times d/365} - P$$

Donde:
- $P$ = principal
- $r$ = tasa anual (%)
- $d$ = días transcurridos
- $n$ = frecuencia de capitalización (1=anual, 4=trimestral, 12=mensual)

### `get_investment_status(db, user_id, investment_id) → InvestmentStatusResponse`

1. Calcula días transcurridos: `(today - start_date).days`
2. Si `current_value` está establecido manualmente → usa ese valor
3. Si no → calcula con `_calculate_return()`
4. Computa:
   - `accrued_interest`: interés acumulado
   - `total_return`: rendimiento total
   - `return_percentage`: rentabilidad %
   - `days_to_maturity`: días hasta vencimiento (o 0 si sin vencimiento)

### `renew_investment(db, user_id, investment_id) → Investment`
- Requiere `auto_renew=True` y `renewal_period_months` configurado
- Extiende `maturity_date` sumando `renewal_period_months`
- Incrementa `renewals_count`

### `get_investment_summary(db, user_id) → InvestmentSummaryResponse`
Agrega todas las inversiones activas:
- Total principal invertido
- Total valor actual estimado
- Rendimiento total y por tipo (`deposit`, `fund`, etc.)

---

## Analytics (`services/analytics.py`)

> Agregaciones sobre transacciones para KPIs y gráficos. Ver [[API_REFERENCE#8. Analytics (`/analytics`)|endpoints de analytics]].

### `get_overview(db, user_id, year, month) → OverviewResponse`
```sql
-- Ingresos del mes
SELECT SUM(amount) FROM transactions
WHERE user_id=X AND amount > 0 AND date BETWEEN inicio AND fin

-- Gastos del mes (valor absoluto)
SELECT SUM(ABS(amount)) FROM transactions
WHERE user_id=X AND amount < 0 AND date BETWEEN inicio AND fin

-- Balance total
SELECT SUM(balance) FROM accounts WHERE user_id=X AND is_active=True
```

### `get_cashflow(db, user_id, months) → List[CashflowMonthResponse]`
- Últimos N meses de ingresos/gastos agrupados por `(year, month)`
- **Rellena con ceros** los meses sin transacciones (importante para gráficos continuos)
- Ordenado cronológicamente

### `get_expenses_by_category(db, user_id, year, month) → List[CategoryExpenseResponse]`
```sql
SELECT c.id, c.name, SUM(ABS(t.amount)), COUNT(t.id)
FROM transactions t JOIN categories c ON t.category_id = c.id
WHERE t.amount < 0 AND t.date BETWEEN inicio AND fin
GROUP BY c.id, c.name
ORDER BY SUM(ABS(t.amount)) DESC
```
- Calcula `percentage = (total_categoría / total_gastos) × 100`

### `get_savings_rate(db, user_id, months) → List[SavingsRateMonthResponse]`
- $\text{Tasa} = \frac{\text{ingresos} - |\text{gastos}|}{\text{ingresos}} \times 100$
- Media móvil 3 meses: promedio de las últimas 3 tasas
- Media móvil 6 meses: promedio de las últimas 6 tasas
- `None` si no hay suficientes meses para la media

### `get_trends(db, user_id, year, month) → TrendsResponse`
Calcula cambios porcentuales:
- `vs_previous_month_pct`: % cambio respecto al mes anterior
- `vs_avg_12m_pct`: % cambio respecto a la media de los últimos 12 meses
- Se calcula para ingresos, gastos y neto

---

## Hipotecas (`services/mortgage.py`)

> Motor de simulación hipotecaria + affordability. Usa funciones puras de `utils/mortgage.py`. Ver [[API_REFERENCE#7. Simulador Hipotecario (`/mortgage`)|endpoints de hipoteca]].

### `simulate_mortgage(data) → MortgageSimulationResult`

**Stateless.** Calcula:
1. `loan_amount = property_price - down_payment`
2. Tabla de amortización según `rate_type`:
   - **Fijo:** Cuota constante toda la vida
   - **Variable:** Euríbor + spread, recalculo cada periodo de revisión
   - **Mixto:** Fijo N años → variable después
3. TAE (Tasa Anual Equivalente) via Newton-Raphson
4. Costes de cierre (opcional)

### `compare_scenarios(data) → MortgageCompareResponse`
Ejecuta `simulate_mortgage()` para cada escenario (2-5) y retorna comparativa.

### `get_affordability(db, user_id, tax_config_id?) → AffordabilityResponse`

1. **Determinar ingresos netos:**
   - Si `tax_config_id` → calcula neto via IRPF (mismo que `/tax/configs/{id}/calculation`)
   - Si no → promedio de ingresos de últimos 3 meses (transacciones)
2. **Máximo pago:** 35% de ingresos netos mensuales
3. **Calcula máximo préstamo** para 6 escenarios estándar:
   - Fijo: 15, 20, 25, 30 años
   - Variable: 20, 30 años

Fórmula inversa del PMT:
$$P_{\max} = \text{PMT}_{\max} \times \frac{(1+r)^n - 1}{r(1+r)^n}$$

### `get_ai_affordability(db, user_id, ...) → AIAffordabilityResponse`

Pipeline de 6 pasos integrando [[ML_SERVICE|servicio ML]]:

1. **Capacidad actual** via `get_affordability()`
2. **Historial** via `analytics.get_cashflow(24 meses)`
3. **Forecast ML** via `ml_client.forecast(months_ahead)`
4. **Ingresos promedio** de predicciones → P10/P50/P90
5. **Euríbor base** desde `MortgageSimulation` más reciente (o default config)
6. **Stress tests** por nivel de Euríbor: para cada nivel, calcula cuota + `is_affordable`

**is_affordable:** $\text{cuota}(\text{Euríbor} + \text{nivel}) \leq 0.35 \times \text{ingreso\_P50}$

---

## Fiscalidad (`services/tax.py`)

> Cálculo IRPF + Seguridad Social. Ver [[DATA_MODELS#TaxBracket|modelo TaxBracket]].

### `seed_tax_brackets(db) → None`

Carga tramos IRPF 2025 y 2026. Idempotente. Ejecutado en `lifespan`.

**Datos fuente:** BOE / Agencia Tributaria

### `calculate_tax(db, user_id, config_id) → TaxCalculationResponse`

Pipeline de cálculo bruto → neto:

```
Bruto anual: 35.000€
  ─ SS (6.50% de 2026): −2.275€
  ─ Gastos trabajo: −2.000€
  = Base imponible: 30.725€
  ─ Mínimo personal: −5.550€ (al 19% = −1.054,50€ de deducción)
  
IRPF por tramos progresivos:
  12.450 × 19% = 2.365,50€
   7.750 × 24% = 1.860,00€
  10.525 × 30% = 3.157,50€
  ──────────────────────────
  Total bruto IRPF: 7.383,00€
  − Deducción mínimo: −1.054,50€
  = IRPF final: 6.328,50€
  
Tipo efectivo: 18.08%
Neto anual: 26.396,50€
Neto mensual: 2.199,71€
```

**Seguridad Social:**
- 2025: 6.35% del bruto
- 2026: 6.50% del bruto
- Base máxima mensual aplicada según normativa

---

## ML Client (`services/ml_client.py`)

> Cliente HTTP async para comunicación con [[ML_SERVICE|microservicio ML]]. Implementa **degradación graceful**.

### Principio de Degradación

```python
async def predict(description, transaction_id=None):
    try:
        response = await httpx.post(f"{ml_url}/predict", json={...})
        return MLPredictResponse(**response.json())
    except (httpx.ConnectError, httpx.TimeoutException):
        return MLPredictResponse(
            ml_available=False,
            category_name="",
            confidence=0.0,
            model_version="unavailable"
        )
```

**Todos los métodos** siguen este patrón: nunca lanzan excepciones al caller, siempre retornan un response degradado con `ml_available=False`.

### Métodos Async (para uso en requests HTTP)

| Método | Destino | Descripción |
|--------|---------|-------------|
| `predict(description, transaction_id?)` | `POST /predict` | Categorización |
| `send_feedback(request)` | `POST /feedback` | Corrección del usuario |
| `get_model_status()` | `GET /model/status` | Estado del modelo |
| `forecast(historical_data, months_ahead)` | `POST /forecast` | Predicción cashflow |

### Métodos Sync (para uso en Celery tasks)

| Método | Destino | Descripción |
|--------|---------|-------------|
| `trigger_retrain_sync()` | `POST /retrain` | Dispara reentrenamiento categorización |
| `trigger_forecast_retrain_sync()` | `POST /forecast/retrain` | Dispara reentrenamiento forecasting |

> [!warning] Sync vs Async
> Los métodos sync usan `httpx.Client` (no async) porque Celery workers corren en un event loop separado. Ver [[CONFIGURATION#Celery|configuración Celery]].

---

## Forecasting (`services/forecasting.py`)

> Orquesta la predicción de cashflow combinando analytics + ML. Ver [[API_REFERENCE#`GET /api/v1/analytics/forecast`|endpoint de forecast]].

### `get_cashflow_forecast(db, user_id, months_ahead) → CashflowForecastResponse`

1. Obtiene hasta 24 meses de histórico via `analytics.get_cashflow()`
2. Transforma a formato ML: `[{income, expenses, year, month}, ...]`
3. Llama `ml_client.forecast(historical_data, months_ahead)`
4. Retorna predicciones P10/P50/P90 + metadata

**Degradación:** Si ML no está disponible, retorna predicciones con valores a 0 y `ml_available=False`.

---

## Escenarios (`services/scenarios.py`)

> Motor what-if stateless con Monte Carlo. Ver [[API_REFERENCE#11. Escenarios What-If (`/scenarios`)|endpoint de escenarios]].

### `analyze_scenario(db, user_id, request) → ScenarioResponse`

**Pipeline de 6 pasos:**

```
1. HISTÓRICO          ─► analytics.get_cashflow(24 meses)
       │
2. DELTA GASTOS       ─► Sumar/restar gastos recurrentes del request
       │
3. IMPACTO EURÍBOR    ─► Buscar MortgageSimulation variable/mixta
       │                  Recalcular cuota con nuevo Euríbor
       │                  Delta = cuota_nueva - cuota_original
       │
4. FORECAST ML        ─► ml_client.forecast(months_ahead)
       │                  P10/P50/P90 de ingresos y gastos
       │
5. CÁLCULO IRPF       ─► _irpf_monthly(gross_annual, tax_year)
       │                  Función pura (sin BD)
       │                  Replica lógica de services/tax.py
       │
6. MONTE CARLO        ─► Por cada mes:
                          - Base: income_p50, expenses_p50
                          - Modificaciones: salary_variation, expense_delta
                          - σ = (P90 - P10) / 2.563
                          - N=1000 muestras normales
                          - Resultado: net_p10, net_p50, net_p90
```

### `_irpf_monthly(gross_annual, tax_year) → Decimal`

Función pura que replica el cálculo IRPF sin acceso a BD:
- SS: 6.35% (2025) o 6.50% (2026)
- Tramos IRPF hardcodeados (mismos que el seeder)
- Retorna neto mensual

> [!note] ¿Por qué duplicar la lógica IRPF?
> El motor de escenarios necesita calcular IRPF con `gross_annual` proporcionado en el request (no un `tax_config_id`). Para evitar dependencia circular con `services/tax.py`, la lógica se reimplementa como función pura.

---

## Monte Carlo (`utils/monte_carlo.py`)

> Funciones puras NumPy para simulación estocástica.

### `simulate_net_distribution(income_p50, income_p10, income_p90, expenses_p50, expenses_p10, expenses_p90, n=1000) → (net_p10, net_p50, net_p90)`

1. Estima σ de ingresos: $\sigma_I = \frac{P90_I - P10_I}{2 \times 1.2816}$ (factor Z para percentil 10/90)
2. Estima σ de gastos: $\sigma_E = \frac{P90_E - P10_E}{2 \times 1.2816}$
3. Genera N muestras: $\text{income}_i \sim \mathcal{N}(\text{P50}_I, \sigma_I)$, $\text{expenses}_i \sim \mathcal{N}(\text{P50}_E, \sigma_E)$
4. $\text{net}_i = \text{income}_i - \text{expenses}_i$
5. Retorna percentiles P10, P50, P90 de la distribución de `net`

### `apply_scenario_modifications(income_p50, expenses_p50, salary_variation_pct, expense_delta) → (new_income, new_expenses)`

Modificaciones deterministas:
- $\text{new\_income} = \text{income} \times (1 + \text{salary\_pct}/100)$
- $\text{new\_expenses} = \text{expenses} + \text{expense\_delta}$

---

## Utilidades Hipotecarias (`utils/mortgage.py`)

> Funciones puras de cálculo financiero.

### `monthly_payment(principal, annual_rate_pct, term_years) → Decimal`

Sistema francés de amortización:
$$\text{PMT} = P \times \frac{r(1+r)^n}{(1+r)^n - 1}$$

Donde $r = \text{tasa\_anual} / (100 \times 12)$ y $n = \text{años} \times 12$.

### `amortization_schedule(principal, annual_rate_pct, term_years, rate_type, ...) → List[AmortizationRow]`

Genera tabla de amortización completa:

**Tipo fijo:** Cuota constante durante toda la vida del préstamo.

**Tipo variable:** Cada periodo de revisión (`review_months`, default 12):
- Recalcula cuota con tasa actual: $\text{rate} = \text{euribor} + \text{spread}$
- Mantiene plazo restante (no extiende)
- Genera fila por cada mes con la tasa aplicada

**Tipo mixto:** Primer periodo fijo (`fixed_years`), luego variable.

### `effective_annual_rate(pmt, principal, term_years) → Decimal`
TAE via **Newton-Raphson** (10 iteraciones, convergencia $\epsilon < 10^{-10}$):
$$\sum_{k=1}^{n} \frac{\text{PMT}}{(1+r)^k} = P$$

### `closing_costs(property_price, property_type, region_tax_rate?) → ClosingCostsResult`

| Concepto | Cálculo |
|----------|---------|
| Notaría | 0.5% del precio |
| Registro | 0.15% del precio |
| Gestoría | 350€ fijo |
| Tasación | 450€ fijo |
| ITP (segunda mano) | 8% del precio (o `region_tax_rate`) |
| AJD (obra nueva) | 1% del precio (o `region_tax_rate`) |

---

## CSV Parser (`utils/csv_parser.py`)

> Parser específico para formato de exportación OpenBank.

### `parse_openbank_csv(content: bytes) → (List[ParsedRow], List[RowParseError])`

**Detección de encoding:**
1. Intenta UTF-8
2. Si `UnicodeDecodeError` → latin-1 (ISO-8859-1)

**Parsing de importe:**
```python
"−1.234,56€"  →  strip("€ ")  →  remove(".")  →  replace(",",".")  →  Decimal("-1234.56")
```

**Parsing de fecha:**
```python
"22/03/2026"  →  datetime.strptime(_, "%d/%m/%Y").date()
```

**Formato esperado:** Header `Fecha;Concepto;Importe;Saldo` con separador `;`.

---

## Logging (`utils/logging.py`)

> Logging estructurado con `structlog`. Ver [[CONFIGURATION#Logging|configuración de logging]].

**Dos modos de operación:**
- **Desarrollo:** `ConsoleRenderer` con colores, timestamps legibles
- **Producción:** `JSONRenderer` para log aggregation (ELK, Datadog, etc.)

**Procesadores compartidos:**
1. `contextvars` — permite binding contextual (request_id, user_id)
2. `add_log_level` — INFO, WARNING, ERROR, etc.
3. `TimeStamper` — ISO 8601
4. `StackInfoRenderer` — para excepciones

**Loggers silenciados en producción:** `uvicorn.access`, `uvicorn.error`, `sqlalchemy.engine`

---

## Tareas Celery (`tasks/`)

> Tareas programadas para reentrenamiento ML. Ver [[CONFIGURATION#Celery|configuración Celery]] y [[ML_SERVICE#Reentrenamiento|reentrenamiento ML]].

### Configuración (`tasks/celery_app.py`)

```python
celery_app = Celery("fincontrol")
celery_app.conf.update(
    broker_url="redis://redis:6379/1",
    result_backend="redis://redis:6379/2",
    timezone="Europe/Madrid",
    enable_utc=True,
)
```

**Beat Schedule:**

| Tarea | Frecuencia | Hora | Descripción |
|-------|-----------|------|-------------|
| `retrain-ml-weekly` | Domingos | 3:00 AM | Reentrenamiento categorización |
| `retrain-forecast-monthly` | Día 1 del mes | 4:00 AM | Reentrenamiento forecasting |

### `trigger_ml_retrain()` — Task de categorización
1. Llama `ml_client.trigger_retrain_sync()`
2. Si hay insufficient feedback → log "skipped"
3. Si ya en progreso → log "in_progress"
4. Si error → log error (nunca lanza excepción)
5. Si éxito → log "started"

### `trigger_forecast_retrain()` — Task de forecasting
Mismo patrón que categorización.

> [!note] Degradación en Celery
> Las tasks nunca lanzan excepciones. Si el ml-service no está disponible, se loguea y se reintenta en el siguiente ciclo de Beat.

---

## Dependencias entre Servicios

```
auth ──────────────────────────────── (independiente)

accounts ──────────────────────────── (independiente)

categories ─── seeder ─────────────── (startup, independiente)

transactions ──► ml_client ─────────► ML_SERVICE (predict)
      │
      └──► categories (para validar category_id)

imports ──────► transactions (create)
      │
      └──► csv_parser (utils)

budgets ──────► transactions (SUM gastos del periodo)

investments ──► accounts (validar ownership)

analytics ────► transactions (agregaciones)
      │
      └──► accounts (balance total)

forecasting ──► analytics (histórico)
      │
      └──► ml_client (forecast)

mortgage ─────► analytics (ingresos para affordability)
      │
      ├──► tax (cálculo neto si tax_config_id)
      │
      ├──► ml_client (AI affordability)
      │
      └──► utils/mortgage (cálculos puros)

scenarios ────► analytics (histórico)
      │
      ├──► ml_client (forecast)
      │
      ├──► mortgage_simulations (impacto Euríbor)
      │
      └──► utils/monte_carlo (simulación)

tax ──────────► seeder (startup, independiente)
```
