---
title: FinControl - Servicio ML
aliases:
  - ML Service
  - Machine Learning
  - IA
  - Categorización
  - Predicción
tags:
  - fincontrol
  - ml
  - machine-learning
  - pytorch
  - distilbert
  - lstm
  - prophet
related:
  - "[[ARCHITECTURE]]"
  - "[[SERVICES]]"
  - "[[API_REFERENCE]]"
  - "[[CONFIGURATION]]"
  - "[[TESTING]]"
status: activo
created: 2026-03-22
updated: 2026-03-22
---

# FinControl - Servicio ML

> [!info] Documentación relacionada
> - [[ARCHITECTURE|Arquitectura]] — Posición del ml-service en la infraestructura
> - [[SERVICES#ML Client|ML Client]] — Cliente HTTP del backend que consume este servicio
> - [[API_REFERENCE#10. ML|Endpoints ML del backend]] — Proxy público del servicio ML
> - [[CONFIGURATION|Configuración]] — Variables de entorno del ml-service
> - [[TESTING|Guía de Testing]] — Tests del servicio ML

---

## Visión General

El **ml-service** es un microservicio FastAPI independiente (puerto 8001) dedicado a tareas de Machine Learning. Corre dentro de Docker Compose con acceso a GPU (NVIDIA runtime) y se comunica con el backend via HTTP interno.

```
┌─────────────────────┐         ┌──────────────────────────────┐
│     Backend         │  HTTP   │      ML Service              │
│   (FastAPI:8000)    │ ──────► │    (FastAPI:8001)             │
│                     │         │                              │
│  services/          │         │  ┌────────────────────────┐  │
│    ml_client.py ────┼────────►│  │ routers/predict.py     │  │
│                     │         │  │ routers/feedback.py    │  │
│  tasks/             │         │  │ routers/retrain.py     │  │
│    ml_retraining ───┼────────►│  │ routers/forecast.py    │  │
│    forecasting   ───┼────────►│  │ routers/model.py       │  │
│                     │         │  │ routers/health.py      │  │
│                     │         │  └────────────────────────┘  │
│                     │         │                              │
│                     │         │  ┌────────────────────────┐  │
│                     │         │  │ ml/model_manager.py    │  │
│                     │         │  │ ml/forecaster.py       │  │
│                     │         │  │ ml/trainer.py          │  │
│                     │         │  │ ml/preprocessor.py     │  │
│                     │         │  │ ml/categories.py       │  │
│                     │         │  │ ml/lstm_model.py       │  │
│                     │         │  └────────────────────────┘  │
│                     │         │              │               │
│                     │         │         ┌────▼────┐          │
│                     │         │         │ Redis   │          │
│                     │         │         │  db 3   │          │
│                     │         │         └─────────┘          │
└─────────────────────┘         └──────────────────────────────┘
```

**Principio fundamental: Degradación graceful.** Si el ml-service no está disponible, el backend sigue funcionando normalmente. Las transacciones se crean sin categoría ML, las predicciones devuelven ceros.

---

## Capacidades

| Capacidad | Modelo | Estado |
|-----------|--------|--------|
| Categorización de transacciones | DistilBERT multilingual fine-tuned | Implementado |
| Predicción de cashflow | LSTM bidireccional + Prophet fallback | Implementado |
| Reentrenamiento automático | Celery Beat + feedback loop | Implementado |
| Inferencia GPU | CUDA via NVIDIA runtime | Configurado |

---

## 1. Categorización Automática

### Modelo: DistilBERT

**Base:** `distilbert-base-multilingual-cased` (Hugging Face)

**Fine-tuning:** Con dataset sintético de ~800 transacciones bancarias españolas (10 categorías × ~80 ejemplos).

**Pipeline de inferencia:**

```
"COMPRA MERCADONA S.A. REF:12345678 22/03/2026"
          │
          ▼  preprocessor.normalize_banking_text()
"COMPRA MERCADONA S.A."
          │
          ▼  tokenizer(max_length=128)
[input_ids, attention_mask]
          │
          ▼  model(tokens)
logits: [0.1, 8.5, 0.3, ...]
          │
          ▼  softmax()
probs: [0.01, 0.95, 0.02, ...]
          │
          ▼  top prediction
("Alimentación", 0.95)
```

### Catálogo de Categorías

El ml-service mantiene un catálogo fijo de 10 categorías (índice → nombre):

| Índice | Categoría |
|--------|-----------|
| 0 | Alimentación |
| 1 | Transporte |
| 2 | Ocio |
| 3 | Hogar |
| 4 | Salud |
| 5 | Educación |
| 6 | Ropa |
| 7 | Tecnología |
| 8 | Ingresos |
| 9 | Otros |

> [!warning] Sincronización con backend
> El ML service usa **nombres** de categoría. El backend resuelve esos nombres a UUIDs del catálogo de sistema via [[SERVICES#Categorías|servicio de categorías]]. Ambos catálogos deben estar sincronizados.

### Preprocessor

`normalize_banking_text(text) → str`

Operaciones de limpieza secuenciales:
1. **Normalización Unicode** (NFC)
2. **Eliminar prefijos bancarios:** `REC DOM`, `TRF`, `COMPRA TRJ`, `COBRO TPV`, `ADEUDO DIRECTO`, `RECIBO`, etc.
3. **Eliminar fechas:** patrones `YYYYMMDD`, `DD/MM/YYYY`, `YYYY-MM-DD`
4. **Eliminar IDs numéricos:** cadenas ≥ 6 dígitos
5. **Normalizar espacios:** múltiples espacios → uno

> [!note] Preservación de case
> No se convierte a minúsculas. DistilBERT multilingual es **cased** y los textos bancarios son mayúsculas.

### Umbrales de Confianza

| Confianza | Acción | Campo response |
|-----------|--------|---------------|
| ≥ 0.92 | Auto-asignar categoría | `auto_assigned=true` |
| 0.50 – 0.91 | Sugerir al usuario | `suggested=true` |
| < 0.50 | Sin sugerencia | Ambos `false` |

Configurables en `ml-service/app/config.py`:
```
categorization_threshold = 0.92
categorization_suggest_threshold = 0.50
```

### ModelManager (Singleton)

`ml-service/app/ml/model_manager.py`

- **Carga:** En `lifespan` de FastAPI, Lee desde `/app/models/categorizer/`
- **Degradado:** Si no hay modelo en disco → `predict()` retorna `("Otros", 0.0)`
- **Hot-reload:** `async reload()` — recarga modelo tras reentrenamiento sin reiniciar
- **Metadata:** `metadata.json` con version, accuracy, trained_at

---

## 2. Predicción de Cashflow

### Modelo: LSTM Bidireccional

**Archivo:** `ml-service/app/ml/lstm_model.py`

**Arquitectura CashflowLSTM:**
```
Input [batch, seq_len=12, 2]    ← (income, expenses) normalizados
         │
    Bidirectional LSTM
    (layers=2, hidden=64, dropout=0.2)
         │
    Output [batch, hidden×2=128]  ← last hidden state
         │
    Fully Connected (128 → 2)
         │
    Output [batch, 2]            ← (income_pred, expenses_pred)
```

**Características clave:**
- **Bidireccional:** Ve la secuencia en ambas direcciones
- **MC Dropout:** Dropout activo durante inferencia → múltiples muestras estocásticas
- **Intervalos de confianza:** 50 forward passes → percentiles P10/P50/P90

### Forecaster (Singleton)

`ml-service/app/ml/forecaster.py`

**Tres niveles de fallback:**

```
1. LSTM         ─► Si modelo cargado desde /app/models/forecaster/
      │              MC Dropout, N=50 muestras
      │              Scaler: StandardScaler guardado con el modelo
      │
      ▼ (fallback si LSTM no disponible)
2. Prophet      ─► Facebook Prophet como baseline estadístico
      │              Seasonality automática, interval_width=0.8
      │
      ▼ (fallback si Prophet falla)
3. Degradado    ─► Devuelve ceros (ml_available=false)
```

**Secuencia de datos (SEQ_LEN=12):**
- Requiere mínimo 12 meses de historial
- Series más cortas → padding con ceros
- Predicción rolling: predice mes N+1, lo añade al contexto, predice N+2, etc.

**Normalización:**
- `scaler.pkl` guardado junto al modelo
- Input/output se transforman con `StandardScaler.transform()` / `inverse_transform()`
- Valores negativos en output → clipping a 0.0

### Almacenamiento de Series

El endpoint `POST /forecast` almacena automáticamente las series históricas recibidas en Redis (`ml:forecast_training`, lista, max 200 entradas) para usar como datos de reentrenamiento.

---

## 3. Reentrenamiento

### Categorización (`POST /retrain`)

**Flujo completo:**

```
POST /retrain
      │
      ├── ¿retrain_in_progress? → 409 Conflict
      │
      ├── Leer feedback de Redis (ml:feedback)
      │
      ├── ¿feedback < min_feedback_for_retrain (10)? → 200 "skipped"
      │
      ├── app.state.retrain_in_progress = True
      │
      ├── ThreadPoolExecutor.submit(run_incremental_retrain)
      │       │
      │       ├── Cargar dataset base + feedback
      │       ├── Train/val split (80/20, stratified)
      │       ├── Fine-tune desde modelo activo
      │       │     - AdamW (lr=2e-5, weight_decay=0.01)
      │       │     - Linear warmup (10% steps)
      │       │     - Gradient clipping (norm=1.0)
      │       │     - Epochs: config.retrain_epochs (2)
      │       │     - Batch: config.retrain_batch_size (16)
      │       ├── Guardar candidato en /models/candidate/
      │       └── Return accuracy
      │
      └── Return 202 "started"

CALLBACK (_on_retrain_complete):
      │
      ├── Comparar accuracy candidato vs activo
      │
      ├── Si acc_candidato ≥ acc_activo − 2%:
      │     ├── Backup metadata activo → /models/history/
      │     ├── Promover candidato → /models/categorizer/
      │     ├── ModelManager.reload()  ← hot-load
      │     └── Archivar feedback procesado en Redis
      │
      └── Si acc_candidato < acc_activo − 2%:
            └── Descartar candidato (approach conservador)
```

**Versionado:** Semántico incremental (1.0 → 1.1 → 1.2...)

### Forecasting (`POST /forecast/retrain`)

Mismo patrón que categorización:
1. Lee series de Redis (`ml:forecast_training`)
2. Filtra series válidas (≥ SEQ_LEN+1 puntos)
3. Requiere mínimo 3 series (`forecast_min_series_for_retrain`)
4. Entrena LSTM en ThreadPoolExecutor
5. Callback con same acceptance logic

### Celery Beat Schedule

| Tarea | Cron | Acción |
|-------|------|--------|
| Categorización | Dom 3:00 AM | `trigger_ml_retrain()` → `POST /retrain` |
| Forecasting | Día 1, 4:00 AM | `trigger_forecast_retrain()` → `POST /forecast/retrain` |

Ver [[SERVICES#Tareas Celery|tareas Celery]] para detalles de implementación.

---

## 4. API del Servicio ML

> [!note] API interna
> Estos endpoints son consumidos por el backend via [[SERVICES#ML Client|MLClient]]. Los usuarios finales acceden a través de los [[API_REFERENCE#10. ML|endpoints proxy del backend]].

### `GET /health`
```json
{
  "app": "FinControl ML Service",
  "env": "development",
  "model_loaded": true
}
```

### `POST /predict`
**Request:**
```json
{
  "description": "COMPRA MERCADONA 1234",
  "transaction_id": "uuid"  // opcional
}
```
**Response:**
```json
{
  "category_id": 0,
  "category_name": "Alimentación",
  "confidence": 0.95,
  "auto_assigned": true,
  "suggested": false,
  "model_version": "1.2"
}
```

### `POST /feedback`
**Request:**
```json
{
  "transaction_id": "uuid",
  "description": "COMPRA MERCADONA 1234",
  "predicted_category_id": 9,
  "correct_category_id": 0
}
```
Almacena en Redis lista `ml:feedback` como JSON.

### `GET /model/status`
```json
{
  "loaded": true,
  "version": "1.2",
  "accuracy": 0.94,
  "last_trained": "2026-03-20T03:00:00Z",
  "feedback_count": 47,
  "retrain_in_progress": false
}
```

### `POST /retrain`
Dispara reentrenamiento async. **Response 202** si iniciado, **200** si skipped, **409** si ya en progreso.

### `POST /forecast`
**Request:**
```json
{
  "historical_data": [
    {"year": 2025, "month": 4, "income": 2500.0, "expenses": 1800.0},
    {"year": 2025, "month": 5, "income": 2600.0, "expenses": 1750.0}
  ],
  "months_ahead": 6,
  "include_intervals": true
}
```
**Response:**
```json
{
  "predictions": [
    {
      "year": 2026, "month": 4,
      "income_p10": 2100.0, "income_p50": 2500.0, "income_p90": 2900.0,
      "expenses_p10": 1500.0, "expenses_p50": 1800.0, "expenses_p90": 2100.0,
      "net_p10": 400.0, "net_p50": 700.0, "net_p90": 1000.0
    }
  ],
  "model_used": "lstm",
  "model_version": "1.0",
  "data_months_provided": 24
}
```

### `POST /forecast/retrain`
Igual que `/retrain` pero para el modelo de forecasting.

### `GET /forecast/status`
```json
{
  "loaded": true,
  "model_version": "1.0",
  "mae": 150.5,
  "retrain_in_progress": false,
  "min_months_required": 12
}
```

---

## 5. Entrenamiento Inicial

### Categorización
```bash
# Generar dataset sintético
cd ml-service
python data/synthetic_dataset.py  # → data/dataset.json (~800 ejemplos)

# Entrenar modelo
python scripts/train.py  # → /app/models/categorizer/ (model + tokenizer + metadata)
```

**Dataset sintético** (`data/synthetic_dataset.py`):
- 10 categorías × ~80 ejemplos
- Textos bancarios realistas en español
- Variaciones de formato, entidades, referencias

### Forecasting
```bash
# Generar series temporales sintéticas
python data/generate_timeseries.py  # → data/timeseries.json (200 series × 36 meses)

# Entrenar LSTM
python scripts/train_forecaster.py  # → /app/models/forecaster/ (model + scaler + metadata)
```

**Dataset sintético** (`data/generate_timeseries.py`):
- 200 series × 36 meses
- 5 perfiles de usuario españoles (asalariado, freelance, doble ingreso, etc.)
- Seasonality, tendencia, ruido realista

---

## 6. Infraestructura

### Docker

**Imagen base:** `pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime`

**Características:**
- Usuario no-root (`mluser`)
- Volume persistente `ml_models:/app/models`
- Health check: `GET /health`
- GPU: `nvidia` runtime (configurable, opcional)
- Redis db 3 (aislado del backend que usa db 0, 1, 2)

### Redis Keys

| Key | Tipo | Descripción |
|-----|------|-------------|
| `ml:feedback` | List | Correcciones del usuario pendientes de reentrenamiento |
| `ml:feedback_archived:{timestamp}` | List | Feedback procesado (archivado) |
| `ml:forecast_training` | List | Series históricas para entrenamiento (max 200) |

### Estado en Memoria (`app.state`)

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `model_manager` | ModelManager | Singleton de categorización |
| `forecaster` | Forecaster | Singleton de predicción |
| `retrain_in_progress` | bool | Lock de reentrenamiento categorización |
| `forecast_retrain_in_progress` | bool | Lock de reentrenamiento forecasting |

---

## 7. Dependencias

```toml
# ML Core
transformers = ">=4.46.0"    # DistilBERT
scikit-learn = ">=1.4"       # StandardScaler, métricas
numpy = ">=1.26.0"           # Arrays, normalización

# Forecasting
prophet = ">=1.1"            # Baseline estadístico (fallback)

# Framework
fastapi = ">=0.115.0"
uvicorn = {version = ">=0.32.0", extras = ["standard"]}
pydantic = ">=2.9.0"
pydantic-settings = ">=2.6.0"

# Storage
redis = ">=5.2.0"            # Feedback + series + locks

# Observability
structlog = ">=24.4.0"       # Logging estructurado
```

> [!note] PyTorch
> PyTorch no está en `pyproject.toml` — viene pre-instalado en la imagen Docker base `pytorch/pytorch:2.5.1`.

---

## 8. Flujo Completo: Creación de Transacción con ML

```
Usuario POST /api/v1/transactions
  │ {description: "COMPRA MERCADONA", category_id: null}
  │
  ▼ Backend: api/v1/transactions.py
  │
  ▼ Service: create_transaction_with_ml()
  │   ├── category_id proporcionado? → crear sin ML
  │   └── Llamar ml_client.predict(description)
  │            │
  │            ▼  HTTP POST http://ml-service:8001/predict
  │            │
  │            ▼  ML Service: model_manager.predict()
  │            │   ├── normalize_banking_text()
  │            │   ├── tokenizer → model → softmax
  │            │   └── return ("Alimentación", 0.95)
  │            │
  │            ▼  Backend recibe MLPredictResponse
  │            │
  │            ├── confianza ≥ 0.92 → buscar UUID de "Alimentación"
  │            │                       → set transaction.category_id
  │            │
  │            ├── 0.50 ≤ conf < 0.92 → response incluye
  │            │                          ml_suggested_category_id
  │            │
  │            └── < 0.50 → sin sugerencia
  │
  ▼ INSERT transaction en BD
  │
  ▼ Response con campos ML
```

```
Usuario corrige categoría
  │
  ▼ POST /api/v1/ml/feedback
  │   {correct_category_id: "uuid-alimentacion"}
  │
  ▼ ml_client.send_feedback()
  │
  ▼ HTTP POST http://ml-service:8001/feedback
  │
  ▼ Redis RPUSH ml:feedback {description, correct_category_id, ...}
  │
  │   ... acumulado hasta Sunday 3AM ...
  │
  ▼ Celery Beat → trigger_ml_retrain()
  │
  ▼ POST http://ml-service:8001/retrain
  │
  ▼ ThreadPoolExecutor → Fine-tune + evaluate
  │
  ▼ Callback → promote/discard → ModelManager.reload()
```
