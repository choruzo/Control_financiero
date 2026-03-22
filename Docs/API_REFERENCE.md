---
title: FinControl - Referencia de API
aliases:
  - API Reference
  - Endpoints
  - REST API
tags:
  - fincontrol
  - api
  - endpoints
  - rest
  - backend
related:
  - "[[ARCHITECTURE]]"
  - "[[DATA_MODELS]]"
  - "[[SERVICES]]"
  - "[[ML_SERVICE]]"
  - "[[CONFIGURATION]]"
status: activo
created: 2026-03-22
updated: 2026-03-22
---

# FinControl - Referencia de API

> [!info] Documentación relacionada
> - [[ARCHITECTURE|Arquitectura del Sistema]] — Visión general y stack tecnológico
> - [[DATA_MODELS|Modelos de Datos]] — Esquemas de base de datos
> - [[SERVICES|Capa de Servicios]] — Lógica de negocio detrás de cada endpoint
> - [[ML_SERVICE|Servicio ML]] — Microservicio de IA (categorización y predicción)
> - [[CONFIGURATION|Configuración y Despliegue]] — Variables de entorno y Docker

---

## Visión General

La API REST de FinControl está expuesta bajo el prefijo `/api/v1/` y documentada automáticamente en **Swagger UI** (`http://localhost:8000/docs`).

**Convenciones:**
- Todos los endpoints protegidos requieren header `Authorization: Bearer <access_token>`
- IDs son **UUID v4**
- Fechas en formato **ISO 8601** (`YYYY-MM-DD` para fechas, `YYYY-MM-DDTHH:MM:SSZ` para timestamps)
- Importes monetarios como `Decimal` con 2 decimales
- Errores siguen el formato `{"detail": "mensaje"}` o `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`

**Códigos de respuesta comunes:**
| Código | Significado |
|--------|-------------|
| 200 | OK — operación exitosa |
| 201 | Created — recurso creado |
| 204 | No Content — recurso eliminado |
| 400 | Bad Request — datos inválidos |
| 401 | Unauthorized — token inválido o ausente |
| 404 | Not Found — recurso no encontrado o no pertenece al usuario |
| 409 | Conflict — duplicado (ej. presupuesto para misma categoría/mes) |
| 422 | Unprocessable Entity — error de validación Pydantic |

---

## 1. Autenticación (`/auth`)

> [!note] Flujo de autenticación
> Registro/Login → access_token (30 min) + refresh_token (7 días) → Bearer token en headers → Refresh cuando expira → Logout revoca refresh token.

### `POST /api/v1/auth/register`
Crea un nuevo usuario.

**Request Body** (JSON):
```json
{
  "email": "usuario@ejemplo.com",
  "password": "miPassword123"
}
```

**Response** `201`:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Validaciones:**
- `email`: formato EmailStr válido, único en BD
- `password`: mínimo 8 caracteres

---

### `POST /api/v1/auth/login`
Autenticación con credenciales. Usa **OAuth2 PasswordRequestForm** (campo `username` = email).

**Request Body** (`application/x-www-form-urlencoded`):
```
username=usuario@ejemplo.com&password=miPassword123
```

**Response** `200`: Token (mismo formato que register)

**Seguridad:** Comparación en tiempo constante para evitar ataques de enumeración de usuarios.

---

### `POST /api/v1/auth/refresh`
Rota el refresh token (revoca el anterior, emite uno nuevo).

**Request Body** (JSON):
```json
{
  "refresh_token": "eyJ..."
}
```

**Response** `200`: Nuevo par de tokens

---

### `GET /api/v1/auth/me` 🔒
Retorna el usuario autenticado.

**Response** `200`:
```json
{
  "id": "uuid",
  "email": "usuario@ejemplo.com",
  "is_active": true,
  "created_at": "2026-03-22T10:00:00Z"
}
```

---

## 2. Cuentas (`/accounts`) 🔒

> [!tip] Relaciones
> Cada cuenta tiene múltiples [[DATA_MODELS#Transactions|transacciones]]. Al eliminar una cuenta, se eliminan en cascada sus transacciones.

### `POST /api/v1/accounts`
Crea una nueva cuenta bancaria.

**Request Body**:
```json
{
  "name": "Cuenta Principal",
  "bank": "OpenBank",
  "account_type": "checking",
  "currency": "EUR",
  "balance": 1500.00
}
```

**account_type**: `checking` | `savings` | `investment` | `credit`

**Response** `201`: `AccountResponse` completo con id y timestamps.

---

### `GET /api/v1/accounts`
Lista todas las cuentas del usuario.

**Response** `200`: `List[AccountResponse]`

---

### `GET /api/v1/accounts/{account_id}`
Obtiene una cuenta por ID. Devuelve 404 si no pertenece al usuario.

---

### `PATCH /api/v1/accounts/{account_id}`
Actualiza campos parciales de una cuenta.

---

### `DELETE /api/v1/accounts/{account_id}`
Elimina una cuenta (cascada: transacciones asociadas). **Response** `204`.

---

## 3. Categorías (`/categories`) 🔒

> [!warning] Categorías de sistema
> Las categorías con `is_system=true` no pueden editarse ni eliminarse. Se crean automáticamente al iniciar la aplicación.

### Categorías por defecto (seeded)

| Categoría | Subcategorías | Icono |
|-----------|--------------|-------|
| Alimentación | Supermercado, Restaurantes | 🛒 |
| Transporte | Combustible, Transporte público, Parking | 🚗 |
| Hogar | Alquiler/Hipoteca, Suministros, Mantenimiento | 🏠 |
| Salud | Farmacia, Médico | 🏥 |
| Ocio | Entretenimiento, Viajes, Deportes | 🎮 |
| Educación | Formación, Libros | 📚 |
| Ropa | Ropa y calzado | 👔 |
| Tecnología | Electrónica, Software/Apps | 💻 |
| Servicios | Seguros, Suscripciones, Telecomunicaciones | 📋 |
| Ingresos | Nómina, Freelance, Inversiones (retornos) | 💰 |
| Transferencias | Transferencias internas | 🔄 |
| Otros | Sin categoría | 📌 |

### `POST /api/v1/categories`
Crea una categoría personalizada.

**Request Body**:
```json
{
  "name": "Mascotas",
  "parent_id": null,
  "color": "#FF6B35",
  "icon": "🐕"
}
```

---

### `GET /api/v1/categories`
Lista categorías del sistema + personalizadas del usuario.

---

### `GET /api/v1/categories/{category_id}` | `PATCH` | `DELETE`
CRUD estándar. Bloquea operaciones de escritura sobre categorías de sistema.

---

## 4. Transacciones (`/transactions`) 🔒

> [!info] Integración ML
> Al crear una transacción sin `category_id`, el sistema invoca al [[ML_SERVICE|servicio ML]] para categorización automática. Ver [[SERVICES#Transacciones|servicio de transacciones]] para detalles del flujo.

### `POST /api/v1/transactions`
Crea una transacción. Si no se proporciona `category_id`, se intenta categorizar con IA.

**Request Body**:
```json
{
  "account_id": "uuid-cuenta",
  "amount": -45.50,
  "description": "COMPRA MERCADONA 1234",
  "transaction_type": "expense",
  "date": "2026-03-22",
  "category_id": null,
  "is_recurring": false,
  "notes": "Compra semanal"
}
```

**transaction_type**: `income` | `expense` | `transfer`
**amount**: Negativo para gastos, positivo para ingresos.

**Response** `201` — incluye campos ML:
```json
{
  "id": "uuid",
  "...campos base...",
  "ml_suggested_category_id": "uuid-alimentacion",
  "ml_confidence": 0.95
}
```

**Lógica ML:**
| Confianza | Acción |
|-----------|--------|
| ≥ 0.92 | Auto-asigna `category_id` |
| 0.50 – 0.91 | Devuelve `ml_suggested_category_id` (sin asignar) |
| < 0.50 | Sin sugerencia |
| ML no disponible | Transacción creada sin categoría |

---

### `GET /api/v1/transactions`
Lista transacciones con filtros y paginación.

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `account_id` | UUID | Filtrar por cuenta |
| `category_id` | UUID | Filtrar por categoría |
| `date_from` | date | Fecha inicio (inclusive) |
| `date_to` | date | Fecha fin (inclusive) |
| `type` | string | `income` / `expense` / `transfer` |
| `skip` | int | Offset (default 0) |
| `limit` | int | Máximo resultados (default 50) |

**Response** `200`:
```json
{
  "items": [...],
  "total": 150,
  "skip": 0,
  "limit": 50
}
```

---

### `POST /api/v1/transactions/import/csv`
Importa transacciones desde archivo CSV formato OpenBank.

**Request:** `multipart/form-data` con archivo CSV.

**Query Parameters:**
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `account_id` | UUID | sí | Cuenta destino |
| `dry_run` | bool | no | Solo validar, no insertar (default false) |

**Formato CSV esperado** (separador `;`, encoding UTF-8 o latin-1):
```csv
Fecha;Concepto;Importe;Saldo
22/03/2026;COMPRA MERCADONA 1234;-45,50;1.454,50
```

**Response** `200`:
```json
{
  "account_id": "uuid",
  "dry_run": false,
  "total_rows": 10,
  "imported": 8,
  "skipped_duplicate": 2,
  "errors": 0,
  "rows": [
    {"row": 1, "status": "imported", "amount": -45.50, "date": "2026-03-22", "transaction_id": "uuid"},
    {"row": 2, "status": "skipped_duplicate", "amount": -30.00, "date": "2026-03-21"}
  ]
}
```

**Deduplicación:** Coincidencia exacta de `fecha + importe + descripción`.

---

### `GET /api/v1/transactions/{id}` | `PATCH` | `DELETE`
CRUD estándar. Todas las operaciones verifican propiedad del usuario.

---

## 5. Presupuestos (`/budgets`) 🔒

> [!tip] Alertas automáticas
> Cuando el gasto acumulado supera el `alert_threshold` (%) del presupuesto, se crea una alerta automáticamente. Ver [[SERVICES#Presupuestos|servicio de presupuestos]].

### `POST /api/v1/budgets`
Crea un presupuesto mensual para una categoría.

**Request Body**:
```json
{
  "category_id": "uuid-alimentacion",
  "period_year": 2026,
  "period_month": 3,
  "limit_amount": 400.00,
  "alert_threshold": 80.00,
  "name": "Presupuesto alimentación marzo"
}
```

**Constraint:** Único por `(user_id, category_id, period_year, period_month)`.

---

### `GET /api/v1/budgets`
Lista presupuestos con filtros opcionales `year` y `month`.

---

### `GET /api/v1/budgets/{id}/status`
Calcula el estado actual del presupuesto.

**Response** `200`:
```json
{
  "budget": { "...campos Budget..." },
  "spent_amount": 320.50,
  "remaining": 79.50,
  "percentage_used": 80.13,
  "is_over_limit": false,
  "alert_triggered": true
}
```

---

### `GET /api/v1/budgets/status`
Estado de todos los presupuestos para un periodo.

**Query Parameters** (requeridos): `period_year`, `period_month`

---

### `GET /api/v1/budgets/alerts`
Lista alertas de presupuesto.

**Query Parameter:** `unread_only` (bool, default false)

---

### `PATCH /api/v1/budgets/alerts/{alert_id}/read`
Marca una alerta como leída.

---

### `GET /{id}` | `PATCH /{id}` | `DELETE /{id}`
CRUD estándar.

---

## 6. Inversiones (`/investments`) 🔒

> [!info] Tipos soportados
> `deposit` (depósito a plazo), `fund` (fondo de inversión), `stock` (acciones), `bond` (bonos). Cada uno tiene cálculo de rendimiento diferente. Ver [[SERVICES#Inversiones|servicio de inversiones]].

### `POST /api/v1/investments`
Registra una nueva inversión.

**Request Body**:
```json
{
  "name": "Depósito Plazo 12M",
  "investment_type": "deposit",
  "principal_amount": 10000.00,
  "interest_rate": 3.25,
  "interest_type": "compound",
  "compounding_frequency": "quarterly",
  "start_date": "2026-01-15",
  "maturity_date": "2027-01-15",
  "auto_renew": true,
  "renewal_period_months": 12,
  "account_id": "uuid-cuenta"
}
```

**Validaciones:**
- Si `interest_type=compound` → `compounding_frequency` requerido
- `maturity_date` > `start_date`
- Si `auto_renew=true` → `renewal_period_months` requerido

---

### `GET /api/v1/investments/summary`
Resumen agregado de todas las inversiones activas agrupadas por tipo.

**Response** `200`:
```json
{
  "total_principal": 25000.00,
  "total_current_value": 25812.50,
  "total_return": 812.50,
  "return_percentage": 3.25,
  "by_type": {
    "deposit": {"count": 2, "principal": 20000.00, "current_value": 20650.00},
    "fund": {"count": 1, "principal": 5000.00, "current_value": 5162.50}
  }
}
```

---

### `GET /api/v1/investments/{id}/status`
Calcula el rendimiento acumulado hasta hoy.

**Response** `200`:
```json
{
  "investment": { "...campos..." },
  "accrued_interest": 162.50,
  "total_return": 162.50,
  "return_percentage": 3.25,
  "days_elapsed": 67,
  "days_to_maturity": 298
}
```

**Cálculo de rendimiento:**
- **Interés simple:** $I = P \times r \times t$
- **Interés compuesto:** $I = P \times (1 + r/n)^{nt} - P$

---

### `POST /api/v1/investments/{id}/renew`
Renueva una inversión (extiende `maturity_date`). Requiere `auto_renew=true` y `renewal_period_months` configurado.

---

### `GET /` | `GET /{id}` | `PATCH /{id}` | `DELETE /{id}`
CRUD estándar. Filtros opcionales: `type`, `is_active`.

---

## 7. Simulador Hipotecario (`/mortgage`) 🔒

> [!info] Documentación detallada
> Ver [[SERVICES#Hipotecas|servicio de hipotecas]] para fórmulas y algoritmos. Ver [[DATA_MODELS#MortgageSimulation|modelo MortgageSimulation]] para simulaciones guardadas.

### `POST /api/v1/mortgage/simulate`
Calcula cuotas, tabla de amortización y costes de cierre. **Stateless** (no guarda en BD).

**Request Body**:
```json
{
  "property_price": 250000.00,
  "down_payment": 50000.00,
  "rate_type": "mixed",
  "term_years": 25,
  "interest_rate": 2.50,
  "euribor_rate": 3.50,
  "spread": 0.80,
  "fixed_years": 5,
  "review_frequency": "annual",
  "property_type": "second_hand",
  "include_closing_costs": true
}
```

**rate_type:**
| Tipo | Campos requeridos |
|------|-------------------|
| `fixed` | `interest_rate` |
| `variable` | `euribor_rate`, `spread` |
| `mixed` | `interest_rate`, `euribor_rate`, `spread`, `fixed_years` |

**Response** `200`:
```json
{
  "loan_amount": 200000.00,
  "rate_type": "mixed",
  "term_years": 25,
  "initial_monthly_payment": 897.22,
  "total_amount_paid": 269166.00,
  "total_interest": 69166.00,
  "effective_annual_rate": 2.78,
  "schedule": [
    {"month": 1, "payment": 897.22, "principal": 480.55, "interest": 416.67, "balance": 199519.45, "applied_rate": 2.50}
  ],
  "closing_costs": {
    "notary": 1250.00,
    "registry": 375.00,
    "tax": 20000.00,
    "gestor": 350.00,
    "appraisal": 450.00,
    "total": 22425.00
  }
}
```

**Fórmulas:**
- **Cuota mensual (PMT):** $\text{PMT} = P \times \frac{r(1+r)^n}{(1+r)^n - 1}$
- **TAE:** Newton-Raphson sobre la ecuación del flujo de pagos
- **Variable:** Recalcula cuota cada periodo de revisión (anual/semestral) manteniendo plazo restante

---

### `POST /api/v1/mortgage/compare`
Compara 2-5 escenarios hipotecarios simultáneamente.

**Request Body**:
```json
{
  "property_price": 250000.00,
  "down_payment": 50000.00,
  "term_years": 25,
  "scenarios": [
    {"rate_type": "fixed", "interest_rate": 2.80},
    {"rate_type": "variable", "euribor_rate": 3.50, "spread": 0.80},
    {"rate_type": "mixed", "interest_rate": 2.50, "euribor_rate": 3.50, "spread": 0.80, "fixed_years": 5}
  ]
}
```

---

### `GET /api/v1/mortgage/affordability`
Calcula la máxima hipoteca que puedes permitirte basándote en tus ingresos reales.

**Query Parameters:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `months` | int | Meses de historial para promedio de ingresos (default 3) |
| `tax_config_id` | UUID | Usar salario neto de configuración fiscal |

**Regla:** Máximo 35% de ingresos netos mensuales para cuota hipotecaria.

**Response** incluye 6 escenarios calculados (fijo 15/20/25/30 años + variable 20/30 años).

---

### `GET /api/v1/mortgage/ai-affordability`
Capacidad hipotecaria basada en **predicción ML de ingresos futuros** + stress tests.

**Query Parameters:**
| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `months_ahead` | int | 12 | Meses a predecir (6-24) |
| `term_years` | int | 25 | Plazo hipoteca (5-40) |
| `tax_config_id` | UUID | — | Config fiscal para cálculo neto |
| `gross_annual` | float | — | Salario bruto anual (alternativa a tax_config) |
| `euribor_stress_levels` | list | [0,1,2,3] | Incrementos Euríbor para stress test |

**Response** `200`:
```json
{
  "forecast_income": {"p10": 1800.00, "p50": 2200.00, "p90": 2600.00},
  "current_affordability": {"monthly_net_income": 2100.00, "max_payment": 735.00},
  "stress_tests": [
    {"euribor_level": 0.0, "max_loan": 175000.00, "monthly_payment": 735.00, "is_affordable": true},
    {"euribor_level": 3.0, "max_loan": 145000.00, "monthly_payment": 735.00, "is_affordable": true}
  ],
  "ml_available": true,
  "model_used": "lstm"
}
```

---

### `POST /simulations` | `GET /simulations` | `GET /simulations/{id}` | `DELETE /simulations/{id}`
CRUD para guardar/recuperar simulaciones hipotecarias.

---

## 8. Analytics (`/analytics`) 🔒

> [!tip] Fuente de datos
> Todos los endpoints de analytics agregan datos de [[DATA_MODELS#Transactions|transacciones]] del usuario. Ver [[SERVICES#Analytics|servicio de analytics]] para detalles de las consultas.

### `GET /api/v1/analytics/overview`
KPIs del mes: ingresos, gastos, ahorro, balance total.

**Query Parameters:** `year` (int), `month` (int) — opcionales, default mes actual.

**Response** `200`:
```json
{
  "year": 2026,
  "month": 3,
  "income": 2500.00,
  "expenses": 1800.00,
  "net_savings": 700.00,
  "savings_rate": 28.00,
  "total_balance": 15420.50,
  "transaction_count": 45
}
```

---

### `GET /api/v1/analytics/cashflow`
Flujo de caja mensual (últimos N meses).

**Query Parameter:** `months` (int, default 12, max 60)

**Response:** Lista de `{year, month, income, expenses, net}` — incluye meses con 0 si no hay transacciones.

---

### `GET /api/v1/analytics/expenses-by-category`
Gastos agrupados por categoría con porcentaje sobre el total.

**Query Parameters:** `year`, `month` (opcionales)

**Response:** Lista de `{category_id, category_name, total_amount, transaction_count, percentage}`

---

### `GET /api/v1/analytics/savings-rate`
Tasa de ahorro mensual con medias móviles.

**Query Parameter:** `months` (int, default 12, max 60)

**Response:** Lista de `{year, month, income, expenses, savings_rate, moving_avg_3m, moving_avg_6m}`

---

### `GET /api/v1/analytics/trends`
Tendencias: cambio porcentual vs mes anterior y vs media de 12 meses.

**Query Parameters:** `year`, `month` (opcionales)

---

### `GET /api/v1/analytics/forecast`
Predicción de flujo de caja con intervalos de confianza P10/P50/P90.

**Query Parameter:** `months` (int, default 6, max 12)

> [!info] Dependencia ML
> Invoca al [[ML_SERVICE|servicio ML]] via `MLClient`. Si el servicio no está disponible, devuelve `ml_available=false` con predicciones a cero. Ver [[SERVICES#Forecasting|servicio de forecasting]].

**Response** `200`:
```json
{
  "predictions": [
    {
      "year": 2026, "month": 4,
      "income_p10": 2100.00, "income_p50": 2500.00, "income_p90": 2900.00,
      "expenses_p10": 1500.00, "expenses_p50": 1800.00, "expenses_p90": 2100.00,
      "net_p10": 400.00, "net_p50": 700.00, "net_p90": 1000.00
    }
  ],
  "model_used": "lstm",
  "model_version": "1.0",
  "historical_months_used": 24,
  "ml_available": true
}
```

---

## 9. Fiscalidad (`/tax`) 🔒

> [!info] Tramos IRPF
> Los tramos se cargan automáticamente al iniciar la aplicación (2025 y 2026). Ver [[SERVICES#Fiscalidad|servicio fiscal]] para la lógica de cálculo.

### `GET /api/v1/tax/brackets`
Lista los tramos IRPF del sistema.

**Query Parameters:** `year` (int), `bracket_type` (`general` | `savings`)

---

### `POST /api/v1/tax/configs`
Crea una configuración fiscal para el usuario.

**Request Body**:
```json
{
  "tax_year": 2026,
  "gross_annual_salary": 35000.00
}
```

**Constraint:** Único por `(user_id, tax_year)`.

---

### `GET /api/v1/tax/configs/{id}/calculation`
Calcula el desglose bruto → neto completo.

**Response** `200`:
```json
{
  "tax_year": 2026,
  "gross_annual": 35000.00,
  "ss_annual": 2275.00,
  "ss_rate": 0.065,
  "work_expenses": 2000.00,
  "taxable_base": 30725.00,
  "personal_allowance": 5550.00,
  "irpf_annual": 4821.75,
  "effective_rate": 0.1378,
  "net_annual": 27903.25,
  "net_monthly": 2325.27,
  "bracket_breakdown": [
    {"from": 0, "to": 12450, "rate": 0.19, "tax": 2365.50},
    {"from": 12450, "to": 20200, "rate": 0.24, "tax": 1860.00}
  ]
}
```

**Fórmula de cálculo:**
$$\text{Neto} = \text{Bruto} - \text{SS} - \text{IRPF}$$

Donde:
- $\text{SS} = \text{Bruto} \times 0.065$ (2026) o $0.0635$ (2025)
- $\text{Base imponible} = \text{Bruto} - \text{SS} - 2000\text{€ (gastos trabajo)}$
- $\text{IRPF} = \sum \text{tramos progresivos} - \text{cuota mínimo personal (5.550€ al 19%)}$

---

### `GET /configs` | `GET /configs/{id}` | `PATCH /configs/{id}` | `DELETE /configs/{id}`
CRUD estándar de configuraciones fiscales.

---

## 10. ML — Categorización y Predicción (`/ml`) 🔒

> [!info] Documentación completa del servicio ML
> Ver [[ML_SERVICE|Servicio ML]] para arquitectura interna, modelos, reentrenamiento y configuración.

### `POST /api/v1/ml/predict`
Predice la categoría de una transacción.

**Request Body**:
```json
{
  "description": "COMPRA MERCADONA 1234",
  "transaction_id": "uuid"
}
```

**Response** `200`:
```json
{
  "category_id": "uuid-alimentacion",
  "category_name": "Alimentación",
  "confidence": 0.95,
  "auto_assigned": true,
  "suggested": false,
  "model_version": "1.2",
  "ml_available": true
}
```

---

### `POST /api/v1/ml/feedback`
Envía corrección del usuario para reentrenamiento.

**Request Body**:
```json
{
  "transaction_id": "uuid",
  "description": "COMPRA MERCADONA 1234",
  "predicted_category_id": "uuid-otros",
  "correct_category_id": "uuid-alimentacion"
}
```

---

### `GET /api/v1/ml/status`
Estado del modelo ML.

**Response** `200`:
```json
{
  "model_loaded": true,
  "version": "1.2",
  "accuracy": 0.94,
  "feedback_count": 47,
  "retrain_in_progress": false,
  "ml_available": true
}
```

---

## 11. Escenarios What-If (`/scenarios`) 🔒

> [!info] Motor Monte Carlo
> Ver [[SERVICES#Escenarios|servicio de escenarios]] para el pipeline completo y las funciones de [[SERVICES#Monte Carlo|Monte Carlo]].

### `POST /api/v1/scenarios/analyze`
Analiza un escenario financiero con variaciones parametrizadas.

**Request Body**:
```json
{
  "name": "Subida sueldo + nuevo coche",
  "months_ahead": 12,
  "salary_variation_pct": 10.0,
  "euribor_variation_pct": 1.5,
  "recurring_expense_modifications": [
    {"description": "Préstamo coche", "monthly_amount": 350.00, "action": "add"},
    {"description": "Gimnasio", "monthly_amount": 50.00, "action": "remove"}
  ],
  "gross_annual": 35000.00,
  "tax_year": 2026,
  "monte_carlo_simulations": 1000
}
```

**Parámetros de modificación:**
| Parámetro | Rango | Descripción |
|-----------|-------|-------------|
| `salary_variation_pct` | -100% a +500% | Variación del sueldo |
| `euribor_variation_pct` | -5 a +15 puntos | Variación del Euríbor |
| `recurring_expense_modifications` | — | Añadir/eliminar gastos recurrentes |
| `gross_annual` | — | Salario bruto para cálculo fiscal |
| `monte_carlo_simulations` | 100 – 5000 | Número de simulaciones MC |

**Response** `200`:
```json
{
  "name": "Subida sueldo + nuevo coche",
  "parameters": { "...request original..." },
  "historical_months_used": 24,
  "ml_available": true,
  "mortgage_impact_per_month": -85.50,
  "monthly_results": [
    {
      "year": 2026, "month": 4,
      "base_income": 2500.00, "base_expenses": 1800.00, "base_net": 700.00,
      "scenario_income": 2750.00, "scenario_expenses": 2100.00,
      "scenario_net_p10": 450.00, "scenario_net_p50": 650.00, "scenario_net_p90": 850.00,
      "tax_delta": -45.00
    }
  ],
  "summary": {
    "period_months": 12,
    "total_base_net": 8400.00,
    "total_scenario_net_p50": 7800.00,
    "absolute_improvement": -600.00,
    "percentage_improvement": -7.14,
    "avg_monthly_improvement": -50.00,
    "total_tax_impact": -540.00
  }
}
```

**Pipeline del motor** (6 pasos):
1. Histórico (24 meses) via analytics
2. Delta gastos de modificaciones recurrentes
3. Impacto Euríbor (busca hipoteca variable/mixta guardada)
4. Forecast ML (predicción de cashflow)
5. Cálculo IRPF puro (sin BD)
6. Monte Carlo por mes → percentiles P10/P50/P90

---

## Health Check

### `GET /health`
Endpoint público (sin autenticación).

**Response** `200`:
```json
{
  "status": "ok",
  "app": "FinControl"
}
```
