---
title: FinControl - Modelos de Datos
aliases:
  - Data Models
  - Database Schema
  - Modelos BD
tags:
  - fincontrol
  - modelos
  - base-de-datos
  - sqlalchemy
  - postgresql
related:
  - "[[ARCHITECTURE]]"
  - "[[API_REFERENCE]]"
  - "[[SERVICES]]"
  - "[[CONFIGURATION]]"
status: activo
created: 2026-03-22
updated: 2026-03-22
---

# FinControl - Modelos de Datos

> [!info] Documentación relacionada
> - [[ARCHITECTURE|Arquitectura]] — Visión general del sistema
> - [[API_REFERENCE|Referencia de API]] — Endpoints que exponen estos modelos
> - [[SERVICES|Capa de Servicios]] — Lógica de negocio que opera sobre los modelos
> - [[CONFIGURATION|Configuración]] — Variables de conexión a BD

---

## Visión General

Todos los modelos están implementados con **SQLAlchemy 2.0 async** y viven en `backend/app/models/`. La base de datos es **PostgreSQL 16** con migraciones gestionadas por **Alembic**.

**Convenciones generales:**
- **Primary Key:** UUID v4 (generado por `uuid4()`)
- **Timestamps:** `created_at` y `updated_at` en UTC
- **Soft delete:** No se usa. Las eliminaciones son reales con cascada.
- **Foreign Keys:** Siempre con `ON DELETE CASCADE` (excepto `category_id` en transacciones → `SET NULL`)
- **Base class:** `DeclarativeBase` de SQLAlchemy (definida en `database.py`)

---

## Diagrama de Relaciones (ER)

```
                                    ┌──────────────────┐
                             ┌──────┤   tax_brackets    │ (system, seeded)
                             │      │ year, type, rate  │
                             │      └──────────────────┘
                             │
┌──────────────┐             │      ┌──────────────────┐
│    users     │─────────────┼─────►│  tax_configs     │
│              │             │      │ year, gross_salary│
│  id (PK)     │             │      └──────────────────┘
│  email       │             │
│  password    │             │      ┌──────────────────┐
│  is_active   │─────────────┼─────►│ refresh_tokens   │
│  created_at  │             │      │ jti, expires_at  │
│  updated_at  │             │      └──────────────────┘
└──────┬───────┘             │
       │                     │      ┌──────────────────┐
       ├─────────────────────┼─────►│   accounts       │
       │                     │      │ name, bank, type │
       │                     │      └────────┬─────────┘
       │                     │               │
       │                     │      ┌────────▼─────────┐
       ├─────────────────────┼─────►│  transactions    │◄─── categories
       │                     │      │ amount, date     │     (FK SET NULL)
       │                     │      └──────────────────┘
       │                     │
       │                     │      ┌──────────────────┐
       ├─────────────────────┼─────►│   budgets        │◄─── categories
       │                     │      │ limit, threshold │     (FK CASCADE)
       │                     │      └────────┬─────────┘
       │                     │               │
       │                     │      ┌────────▼─────────┐
       │                     │      │  budget_alerts   │
       │                     │      │ spent, percentage│
       │                     │      └──────────────────┘
       │                     │
       │                     │      ┌──────────────────┐
       ├─────────────────────┼─────►│  investments     │◄─── accounts
       │                     │      │ principal, rate  │     (FK SET NULL)
       │                     │      └──────────────────┘
       │                     │
       └─────────────────────┼─────►┌──────────────────┐
                             │      │ mortgage_sims    │
                             │      │ price, rate_type │
                             │      └──────────────────┘
                             │
                             │      ┌──────────────────┐
                             └─────►│  categories      │
                                    │ name, parent_id  │◄─── self (hierarchy)
                                    │ is_system        │
                                    └──────────────────┘
```

---

## Detalle de Modelos

### User

> **Archivo:** `backend/app/models/user.py`
> **Tabla:** `users`
> **Migración:** `0001_create_users_and_refresh_tokens.py`

Modelo central. Todos los demás modelos tienen `user_id` como FK.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | Primary Key |
| `email` | VARCHAR(255) | No | — | Unique, Indexed |
| `hashed_password` | VARCHAR(255) | No | — | Bcrypt (12 rounds) |
| `is_active` | BOOLEAN | No | `True` | — |
| `created_at` | DATETIME | No | `utcnow()` | — |
| `updated_at` | DATETIME | No | `utcnow()` | Auto-update |

**Relaciones (1→N, cascade delete):**
- `refresh_tokens` → RefreshToken
- `accounts` → Account
- `categories` → Category (custom)
- `transactions` → Transaction
- `budgets` → Budget
- `investments` → Investment
- `mortgage_simulations` → MortgageSimulation
- `tax_configs` → TaxConfig

> [!note] Uso en API
> Expuesto via [[API_REFERENCE#1. Autenticación (`/auth`)|endpoints de autenticación]]. La contraseña nunca se expone en responses.

---

### RefreshToken

> **Archivo:** `backend/app/models/refresh_token.py`
> **Tabla:** `refresh_tokens`
> **Migración:** `0001_create_users_and_refresh_tokens.py`

Almacena refresh tokens para rotación segura.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `user_id` | UUID (FK) | No | — | → users.id, CASCADE |
| `jti` | UUID | No | — | JWT ID, Unique (para revocación) |
| `expires_at` | DATETIME | No | — | UTC |
| `revoked` | BOOLEAN | No | `False` | Se marca True al rotar |
| `created_at` | DATETIME | No | `utcnow()` | — |

**Flujo de rotación:** Login → crea token → Refresh → revoca anterior + crea nuevo → Logout → revoca todos.

---

### Account

> **Archivo:** `backend/app/models/account.py`
> **Tabla:** `accounts`
> **Migración:** `0002_add_accounts_categories_transactions.py`

Cuentas bancarias del usuario.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `user_id` | UUID (FK) | No | — | → users.id, CASCADE, Indexed |
| `name` | VARCHAR(100) | No | — | Ej: "Cuenta Principal" |
| `bank` | VARCHAR(100) | Sí | — | Ej: "OpenBank" |
| `account_type` | VARCHAR(20) | No | — | `checking` \| `savings` \| `investment` \| `credit` |
| `currency` | VARCHAR(3) | No | `EUR` | ISO 4217 |
| `balance` | DECIMAL(14,2) | No | `0` | Saldo actual |
| `is_active` | BOOLEAN | No | `True` | — |
| `created_at` | DATETIME | No | `utcnow()` | — |
| `updated_at` | DATETIME | No | `utcnow()` | Auto-update |

**Relaciones:**
- 1→N `transactions` (cascade delete)
- 1→N `investments` (SET NULL en FK)

> [!warning] Cascada
> Eliminar una cuenta elimina **todas** sus transacciones. Las inversiones asociadas se desvinculan (`account_id = NULL`).

---

### Category

> **Archivo:** `backend/app/models/category.py`
> **Tabla:** `categories`
> **Migración:** `0002_add_accounts_categories_transactions.py`

Categorías jerárquicas para clasificar transacciones. Incluye categorías de sistema (seeded) y personalizadas.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `user_id` | UUID (FK) | **Sí** | — | NULL = categoría de sistema, Indexed |
| `parent_id` | UUID (FK) | Sí | — | → categories.id (auto-referencial) |
| `name` | VARCHAR(100) | No | — | — |
| `color` | VARCHAR(7) | Sí | — | Formato `#RRGGBB` |
| `icon` | VARCHAR(50) | Sí | — | Emoji o nombre de icono |
| `is_system` | BOOLEAN | No | `False` | Protegidas de edición/borrado |
| `created_at` | DATETIME | No | `utcnow()` | — |
| `updated_at` | DATETIME | No | `utcnow()` | Auto-update |

**Jerarquía auto-referencial:**
```
Alimentación (parent)
  ├── Supermercado (child, parent_id = Alimentación.id)
  └── Restaurantes (child)
```

**Seeder:** 12 categorías raíz + 27 subcategorías, ejecutado en `lifespan` de FastAPI. Idempotente (no duplica si ya existe).

**Relación con ML:** Las categorías de sistema se sincronizan con el catálogo fijo del [[ML_SERVICE#Catálogo de Categorías|servicio ML]] (10 categorías base que mapean por nombre).

---

### Transaction

> **Archivo:** `backend/app/models/transaction.py`
> **Tabla:** `transactions`
> **Migración:** `0002_add_accounts_categories_transactions.py`

Movimientos financieros. Modelo central de la aplicación.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `account_id` | UUID (FK) | No | — | → accounts.id, CASCADE, Indexed |
| `user_id` | UUID (FK) | No | — | → users.id, CASCADE, Indexed |
| `category_id` | UUID (FK) | **Sí** | — | → categories.id, **SET NULL**, Indexed |
| `amount` | DECIMAL(14,2) | No | — | Negativo = gasto, positivo = ingreso |
| `description` | VARCHAR(255) | No | — | Concepto bancario |
| `transaction_type` | VARCHAR(10) | No | — | `income` \| `expense` \| `transfer` |
| `date` | DATE | No | — | Indexed |
| `is_recurring` | BOOLEAN | No | `False` | — |
| `recurrence_rule` | VARCHAR(50) | Sí | — | `daily` \| `weekly` \| `monthly` \| `yearly` |
| `notes` | TEXT | Sí | — | — |
| `created_at` | DATETIME | No | `utcnow()` | — |
| `updated_at` | DATETIME | No | `utcnow()` | Auto-update |

> [!info] Campos ML en el response (no en BD)
> `ml_suggested_category_id` y `ml_confidence` se calculan en tiempo real al crear la transacción y se devuelven en el schema `TransactionResponse`, pero **no se persisten en la tabla**. La categoría auto-asignada sí se guarda en `category_id`.

**Importación CSV:** El [[SERVICES#Importación CSV|servicio de importación]] deduplica por `(date, amount, description)` antes de insertar.

**Índices:** `account_id`, `user_id`, `category_id`, `date` — optimizados para las queries de [[API_REFERENCE#8. Analytics (`/analytics`)|analytics]].

---

### Budget

> **Archivo:** `backend/app/models/budget.py`
> **Tabla:** `budgets`
> **Migración:** `0003_add_budgets.py`

Presupuestos mensuales por categoría.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `user_id` | UUID (FK) | No | — | → users.id, CASCADE, Indexed |
| `category_id` | UUID (FK) | No | — | → categories.id, CASCADE, Indexed |
| `period_year` | INTEGER | No | — | Año del presupuesto |
| `period_month` | INTEGER | No | — | Mes (1-12) |
| `limit_amount` | DECIMAL(14,2) | No | — | Límite de gasto |
| `alert_threshold` | DECIMAL(5,2) | No | `80.00` | % a partir del cual crear alerta |
| `name` | VARCHAR(100) | Sí | — | Nombre descriptivo opcional |
| `created_at` | DATETIME | No | `utcnow()` | — |
| `updated_at` | DATETIME | No | `utcnow()` | Auto-update |

**Constraint:** `UNIQUE (user_id, category_id, period_year, period_month)` — un presupuesto por categoría/mes.

---

### BudgetAlert

> **Archivo:** `backend/app/models/budget.py` (mismo archivo que Budget)
> **Tabla:** `budget_alerts`
> **Migración:** `0003_add_budgets.py`

Alertas generadas automáticamente cuando un presupuesto supera su umbral.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `budget_id` | UUID (FK) | No | — | → budgets.id, CASCADE, Indexed |
| `triggered_at` | DATETIME | No | `utcnow()` | Momento del trigger |
| `spent_amount` | DECIMAL(14,2) | No | — | Gasto al momento del trigger |
| `percentage` | DECIMAL(6,2) | No | — | % consumido al momento |
| `is_read` | BOOLEAN | No | `False` | Marcable via API |

> [!tip] Lógica de alertas
> Las alertas se crean automáticamente en [[SERVICES#Presupuestos|`get_budget_status()`]] cuando `percentage_used >= alert_threshold`. Solo se crea una alerta por umbral alcanzado.

---

### Investment

> **Archivo:** `backend/app/models/investment.py`
> **Tabla:** `investments`
> **Migración:** `0004_add_investments.py`

Productos de inversión: depósitos, fondos, acciones, bonos.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `user_id` | UUID (FK) | No | — | → users.id, CASCADE, Indexed |
| `account_id` | UUID (FK) | **Sí** | — | → accounts.id, **SET NULL**, Indexed |
| `name` | VARCHAR(100) | No | — | — |
| `investment_type` | VARCHAR(20) | No | — | `deposit` \| `fund` \| `stock` \| `bond` |
| `principal_amount` | DECIMAL(14,2) | No | — | Capital invertido |
| `interest_rate` | DECIMAL(6,4) | No | — | Ej: 4.2500 = 4.25% |
| `interest_type` | VARCHAR(10) | No | — | `simple` \| `compound` |
| `compounding_frequency` | VARCHAR(10) | Sí | — | `annually` \| `quarterly` \| `monthly` |
| `current_value` | DECIMAL(14,2) | Sí | — | Valor de mercado manual |
| `start_date` | DATE | No | — | Indexed |
| `maturity_date` | DATE | Sí | — | NULL si sin vencimiento |
| `auto_renew` | BOOLEAN | No | `False` | — |
| `renewal_period_months` | INTEGER | Sí | — | Meses a extender |
| `renewals_count` | INTEGER | No | `0` | Contador de renovaciones |
| `notes` | TEXT | Sí | — | — |
| `is_active` | BOOLEAN | No | `True` | — |
| `created_at` | DATETIME | No | `utcnow()` | — |
| `updated_at` | DATETIME | No | `utcnow()` | Auto-update |

**Cálculo de rendimiento:** Ver [[SERVICES#Inversiones|servicio de inversiones]] para las fórmulas de interés simple y compuesto.

---

### MortgageSimulation

> **Archivo:** `backend/app/models/mortgage.py`
> **Tabla:** `mortgage_simulations`
> **Migración:** `0005_add_mortgage_simulations.py`

Simulaciones hipotecarias guardadas por el usuario.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `user_id` | UUID (FK) | No | — | → users.id, CASCADE, Indexed |
| `name` | VARCHAR(150) | No | — | Nombre identificativo |
| **Parámetros de entrada** | | | | |
| `property_price` | DECIMAL(14,2) | No | — | Precio del inmueble |
| `down_payment` | DECIMAL(14,2) | No | — | Entrada |
| `loan_amount` | DECIMAL(14,2) | No | — | Importe del préstamo |
| `rate_type` | VARCHAR(10) | No | — | `fixed` \| `variable` \| `mixed` |
| `term_years` | INTEGER | No | — | Plazo en años |
| `interest_rate` | DECIMAL(6,4) | Sí | — | Para fijo/mixto |
| `euribor_rate` | DECIMAL(6,4) | Sí | — | Para variable/mixto |
| `spread` | DECIMAL(6,4) | Sí | — | Diferencial |
| `fixed_years` | INTEGER | Sí | — | Años fijo en mixta |
| `review_frequency` | VARCHAR(10) | Sí | — | `annual` \| `semiannual` |
| `property_type` | VARCHAR(15) | No | `second_hand` | `new` \| `second_hand` |
| `region_tax_rate` | DECIMAL(6,4) | Sí | — | Override ITP/AJD |
| **Resultados pre-calculados** | | | | |
| `initial_monthly_payment` | DECIMAL(12,2) | No | — | Primera cuota |
| `total_amount_paid` | DECIMAL(14,2) | No | — | Total pagado |
| `total_interest` | DECIMAL(14,2) | No | — | Total intereses |
| `created_at` | DATETIME | No | `utcnow()` | — |
| `updated_at` | DATETIME | No | `utcnow()` | Auto-update |

> [!note] Uso en escenarios
> La tabla se consulta en [[SERVICES#Escenarios|servicios de escenarios]] para calcular el impacto del Euríbor: busca la simulación variable/mixta más reciente del usuario.

---

### TaxBracket

> **Archivo:** `backend/app/models/tax.py`
> **Tabla:** `tax_brackets`
> **Migración:** `0006_add_tax.py`

Tramos IRPF del sistema. **Datos de referencia** (seeded, no editables por usuario).

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `tax_year` | INTEGER | No | — | Indexed |
| `bracket_type` | VARCHAR(10) | No | — | `general` \| `savings` (ahorro) |
| `min_amount` | DECIMAL(14,2) | No | — | Límite inferior del tramo |
| `max_amount` | DECIMAL(14,2) | **Sí** | — | NULL para el tramo superior |
| `rate` | DECIMAL(5,4) | No | — | Ej: 0.1900 = 19% |
| `created_at` | DATETIME | No | `utcnow()` | — |

**Datos seeded (escala general 2026):**

| Desde | Hasta | Tipo marginal |
|-------|-------|---------------|
| 0€ | 12.450€ | 19% |
| 12.450€ | 20.200€ | 24% |
| 20.200€ | 35.200€ | 30% |
| 35.200€ | 60.000€ | 37% |
| 60.000€ | 300.000€ | 45% |
| 300.000€ | ∞ | 47% |

---

### TaxConfig

> **Archivo:** `backend/app/models/tax.py`
> **Tabla:** `tax_configs`
> **Migración:** `0006_add_tax.py`

Configuración fiscal del usuario por año.

| Columna | Tipo | Nullable | Default | Notas |
|---------|------|----------|---------|-------|
| `id` | UUID | No | `uuid4()` | PK |
| `user_id` | UUID (FK) | No | — | → users.id, CASCADE, Indexed |
| `tax_year` | INTEGER | No | — | — |
| `gross_annual_salary` | DECIMAL(14,2) | No | — | Salario bruto anual |
| `created_at` | DATETIME | No | `utcnow()` | — |
| `updated_at` | DATETIME | No | `utcnow()` | Auto-update |

**Constraint:** `UNIQUE (user_id, tax_year)` — una configuración por año.

**Integración:** Usado opcionalmente por [[API_REFERENCE#`GET /api/v1/mortgage/affordability`|/mortgage/affordability]] para calcular ingresos netos reales via IRPF en lugar de promediar transacciones.

---

## Migraciones Alembic

Las migraciones se encuentran en `backend/alembic/versions/`:

| Archivo | Descripción | Tablas |
|---------|-------------|--------|
| `0001_create_users_and_refresh_tokens.py` | Autenticación | `users`, `refresh_tokens` |
| `0002_add_accounts_categories_transactions.py` | Core financiero | `accounts`, `categories`, `transactions` |
| `0003_add_budgets.py` | Presupuestos | `budgets`, `budget_alerts` |
| `0004_add_investments.py` | Inversiones | `investments` |
| `0005_add_mortgage_simulations.py` | Hipotecas | `mortgage_simulations` |
| `0006_add_tax.py` | Fiscalidad | `tax_brackets`, `tax_configs` |

**Comandos:**
```bash
# Crear nueva migración
docker compose -f docker-compose.dev.yml exec backend alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones pendientes
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Revertir última migración
docker compose -f docker-compose.dev.yml exec backend alembic downgrade -1
```

---

## Convenciones de Datos

### Cantidades monetarias
- Tipo: `DECIMAL(14,2)` — hasta 999.999.999.999,99€
- Sin redondeo por floating-point (Python `Decimal`)
- El signo indica dirección: negativo = gasto, positivo = ingreso

### Porcentajes
- Tipo: `DECIMAL(5,2)` o `DECIMAL(6,4)` según precisión necesaria
- Almacenados como valor directo: `80.00` = 80%, `0.1900` = 19%

### Fechas y timestamps
- `DATE` para fechas de transacciones, inversiones, etc.
- `DATETIME` con UTC para timestamps de auditoría
- Python usa `datetime.utcnow()` para generación

### UUIDs
- Tipo PostgreSQL nativo `UUID` via `sa.UUID(as_uuid=True)`
- Generados en Python con `uuid.uuid4()`
- Nunca expuestos como enteros secuenciales (seguridad)
