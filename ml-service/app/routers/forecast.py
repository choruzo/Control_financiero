"""
Router de predicción de flujo de caja.

Expone:
- POST /forecast         — predice cashflow para los próximos N meses
- POST /forecast/retrain — dispara reentrenamiento del modelo LSTM
- GET  /forecast/status  — estado del modelo de forecasting

El endpoint /forecast almacena los datos históricos recibidos en Redis para que
el ciclo de reentrenamiento pueda aprender de datos reales de usuarios.

El reentrenamiento sigue el mismo patrón que /retrain de categorización:
corre en ThreadPoolExecutor y devuelve 202 inmediatamente.
"""

from __future__ import annotations

import asyncio
import json
import pickle
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    ForecastRetrainResponse,
    ForecastStatusResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/forecast", tags=["forecast"])

FORECAST_TRAINING_KEY = "ml:forecast_training"
MAX_STORED_SERIES = 200

# ThreadPoolExecutor dedicado (máximo 1 tarea simultánea)
_forecast_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="forecast_retrain")

SEQ_LEN = 12


@router.post("", response_model=ForecastResponse)
async def forecast(req: Request, body: ForecastRequest):
    """
    Predice el flujo de caja para los próximos N meses.

    Usa LSTM si está entrenado, Prophet como fallback estadístico,
    o devuelve ceros en modo degradado.
    Almacena los datos históricos en Redis para futuros reentrenamientos.
    """
    forecaster = getattr(req.app.state, "forecaster", None)
    if forecaster is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Forecaster no inicializado"},
        )

    historical = [d.model_dump() for d in body.historical_data]
    predictions, model_used = forecaster.predict(
        historical_data=historical,
        months_ahead=body.months_ahead,
    )

    # Almacenar datos históricos en Redis para reentrenamiento (best-effort)
    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        series_json = json.dumps([[d["income"], d["expenses"]] for d in historical])
        await redis.rpush(FORECAST_TRAINING_KEY, series_json)
        # Mantener máximo MAX_STORED_SERIES entradas
        list_len = await redis.llen(FORECAST_TRAINING_KEY)
        if list_len > MAX_STORED_SERIES:
            await redis.ltrim(FORECAST_TRAINING_KEY, list_len - MAX_STORED_SERIES, -1)
        await redis.aclose()
    except Exception as exc:
        logger.debug("forecast_redis_store_failed", error=str(exc))

    status = forecaster.get_status()
    version = status.get("version") or "degraded"

    return ForecastResponse(
        predictions=predictions,
        model_used=model_used,
        model_version=version,
        data_months_provided=len(body.historical_data),
    )


@router.post("/retrain", response_model=ForecastRetrainResponse)
async def trigger_forecast_retrain(req: Request):
    """
    Dispara un ciclo de reentrenamiento del modelo LSTM de forecasting.

    Lee las series históricas almacenadas en Redis, las combina con datos
    sintéticos y reentrena. Devuelve 202 inmediatamente; el training corre
    en background.

    Respuestas:
    - **202**: Reentrenamiento iniciado.
    - **200**: Datos insuficientes, reentrenamiento omitido.
    - **409**: Ya hay un reentrenamiento en curso.
    - **503**: Redis no disponible.
    """
    if getattr(req.app.state, "forecast_retrain_in_progress", False):
        return JSONResponse(
            status_code=409,
            content={
                "status": "in_progress",
                "data_series_count": 0,
                "reason": "Reentrenamiento ya en curso",
                "model_version": None,
            },
        )

    # Leer series acumuladas de Redis
    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        raw_series = await redis.lrange(FORECAST_TRAINING_KEY, 0, -1)
        await redis.aclose()
    except Exception as exc:
        logger.warning("forecast_retrain_redis_error", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "data_series_count": 0,
                "reason": f"Redis no disponible: {exc}",
                "model_version": None,
            },
        )

    # Parsear series válidas (longitud mínima SEQ_LEN + 1)
    valid_series: list[list[list[float]]] = []
    for raw in raw_series:
        try:
            series = json.loads(raw)
            if isinstance(series, list) and len(series) >= SEQ_LEN + 1:
                valid_series.append(series)
        except (json.JSONDecodeError, TypeError):
            continue

    if len(valid_series) < settings.forecast_min_series_for_retrain:
        logger.info(
            "forecast_retrain_skipped",
            valid_series=len(valid_series),
            min_required=settings.forecast_min_series_for_retrain,
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": "skipped",
                "data_series_count": len(valid_series),
                "reason": (
                    f"Series insuficientes (mínimo: {settings.forecast_min_series_for_retrain})"
                ),
                "model_version": None,
            },
        )

    req.app.state.forecast_retrain_in_progress = True
    source_path = Path(settings.forecast_model_path) / "forecaster"
    candidate_path = Path(settings.forecast_model_path) / "forecaster_candidate"
    current_version = (
        req.app.state.forecaster.metadata.get("version", "1.0")
        if hasattr(req.app.state, "forecaster")
        else "1.0"
    )
    app = req.app
    loop = asyncio.get_running_loop()

    def _run_sync() -> None:
        try:
            metadata = _run_forecast_retrain(
                source_path=source_path,
                output_path=candidate_path,
                training_series=valid_series,
                epochs=settings.forecast_retrain_epochs,
                batch_size=settings.forecast_retrain_batch_size,
                device=settings.device,
                current_version=current_version,
            )
            asyncio.run_coroutine_threadsafe(
                _on_retrain_complete(app, metadata, success=True),
                loop,
            )
        except Exception as exc:
            logger.error("forecast_retrain_thread_failed", error=str(exc))
            asyncio.run_coroutine_threadsafe(
                _on_retrain_complete(app, {}, success=False),
                loop,
            )

    loop.run_in_executor(_forecast_executor, _run_sync)

    logger.info(
        "forecast_retrain_started",
        series_count=len(valid_series),
        version=current_version,
    )
    return JSONResponse(
        status_code=202,
        content={
            "status": "started",
            "data_series_count": len(valid_series),
            "reason": None,
            "model_version": current_version,
        },
    )


@router.get("/status", response_model=ForecastStatusResponse)
async def forecast_status(req: Request):
    """Estado actual del modelo de forecasting."""
    forecaster = getattr(req.app.state, "forecaster", None)
    if forecaster is None:
        return ForecastStatusResponse(
            loaded=False,
            model_version=None,
            mae=None,
            retrain_in_progress=False,
            min_months_required=settings.forecast_min_months,
        )

    status = forecaster.get_status()
    return ForecastStatusResponse(
        loaded=status["loaded"],
        model_version=status.get("version"),
        mae=status.get("mae"),
        retrain_in_progress=getattr(req.app.state, "forecast_retrain_in_progress", False),
        min_months_required=settings.forecast_min_months,
        last_trained=status.get("last_trained"),
    )


# ---------------------------------------------------------------------------
# Lógica de reentrenamiento (ejecutada en ThreadPoolExecutor)
# ---------------------------------------------------------------------------

def _run_forecast_retrain(
    source_path: Path,
    output_path: Path,
    training_series: list[list[list[float]]],
    epochs: int,
    batch_size: int,
    device: str,
    current_version: str,
) -> dict:
    """
    Reentrena el modelo LSTM sobre las series proporcionadas.

    Crea ventanas deslizantes (SEQ_LEN → siguiente mes) como ejemplos de training.
    Guarda el candidato en output_path y devuelve metadata con la MAE en validación.
    """
    import torch
    import torch.nn as nn
    from sklearn.preprocessing import StandardScaler
    from torch.utils.data import DataLoader, TensorDataset

    from app.ml.lstm_model import CashflowLSTM

    # Construir dataset con ventanas deslizantes
    X_list: list[np.ndarray] = []
    y_list: list[np.ndarray] = []

    for series in training_series:
        arr = np.array(series, dtype=np.float32)
        for i in range(len(arr) - SEQ_LEN):
            X_list.append(arr[i : i + SEQ_LEN])
            y_list.append(arr[i + SEQ_LEN])

    if not X_list:
        raise ValueError("No se generaron ejemplos de entrenamiento con los datos proporcionados")

    X = np.array(X_list, dtype=np.float32)  # [N, SEQ_LEN, 2]
    y = np.array(y_list, dtype=np.float32)  # [N, 2]

    # Normalizar con scaler ajustado sobre todos los valores
    all_values = np.vstack([X.reshape(-1, 2), y])
    scaler = StandardScaler()
    scaler.fit(all_values)

    X_flat = X.reshape(-1, 2)
    X_scaled = scaler.transform(X_flat).reshape(X.shape).astype(np.float32)
    y_scaled = scaler.transform(y).astype(np.float32)

    # Split 80/20
    n = len(X_scaled)
    split = max(1, int(n * 0.8))
    X_train, X_val = X_scaled[:split], X_scaled[split:]
    y_train, y_val = y_scaled[:split], y_scaled[split:]

    # DataLoaders
    train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    # Cargar modelo base si existe, sino inicializar desde cero
    model = CashflowLSTM()
    if source_path.exists() and (source_path / "model.pt").exists():
        try:
            model.load_state_dict(
                torch.load(str(source_path / "model.pt"), map_location=device, weights_only=True)
            )
            logger.info("forecast_retrain_loaded_base", path=str(source_path))
        except Exception as exc:
            logger.warning("forecast_retrain_base_load_failed", error=str(exc))

    model.to(device)
    model.train()

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    for epoch in range(epochs):
        total_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        logger.debug(
            "forecast_epoch",
            epoch=epoch + 1,
            loss=round(total_loss / max(len(train_loader), 1), 6),
        )

    # Evaluar MAE en validación (escala original)
    model.eval()
    mae = float("inf")
    if len(X_val) > 0:
        X_val_t = torch.from_numpy(X_val).to(device)
        with torch.no_grad():
            y_pred_scaled = model(X_val_t).cpu().numpy()
        y_pred = scaler.inverse_transform(y_pred_scaled)
        y_true = scaler.inverse_transform(y_val)
        mae = float(np.mean(np.abs(y_pred - y_true)))

    # Calcular nueva versión
    try:
        major, minor = current_version.split(".", 1)
        new_version = f"{major}.{int(minor) + 1}"
    except (ValueError, AttributeError):
        new_version = "1.1"

    # Guardar candidato
    output_path.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(output_path / "model.pt"))
    with open(output_path / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    metadata = {
        "version": new_version,
        "mae": round(mae, 4),
        "trained_at": datetime.now(UTC).isoformat(),
        "training_series": len(training_series),
        "training_examples": len(X_list),
    }
    (output_path / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    logger.info(
        "forecast_retrain_complete",
        version=new_version,
        mae=round(mae, 4),
        examples=len(X_list),
    )
    return metadata


async def _on_retrain_complete(app, metadata: dict, success: bool) -> None:
    """Callback async ejecutado en el event loop tras completar el training."""
    try:
        if not success:
            logger.error("forecast_retrain_failed_cleaning_up")
            return

        candidate_path = Path(settings.forecast_model_path) / "forecaster_candidate"
        active_path = Path(settings.forecast_model_path) / "forecaster"

        candidate_mae = metadata.get("mae", float("inf"))
        active_mae = app.state.forecaster.metadata.get("mae", float("inf"))

        # Promover si el candidato no es significativamente peor (tolerancia 10%)
        if active_mae == float("inf") or candidate_mae <= active_mae * 1.1:
            _backup_active_metadata(active_path)

            if candidate_path.exists():
                if active_path.exists():
                    shutil.rmtree(str(active_path))
                shutil.move(str(candidate_path), str(active_path))

            await app.state.forecaster.reload()

            logger.info(
                "forecaster_promoted",
                new_version=metadata.get("version"),
                new_mae=candidate_mae,
                old_mae=active_mae,
            )
        else:
            if candidate_path.exists():
                shutil.rmtree(str(candidate_path))
            logger.warning(
                "forecaster_rejected",
                candidate_mae=candidate_mae,
                active_mae=active_mae,
            )
    finally:
        app.state.forecast_retrain_in_progress = False


def _backup_active_metadata(active_path: Path) -> None:
    """Copia el metadata del modelo activo al historial antes de sobrescribirlo."""
    metadata_file = active_path / "metadata.json"
    if not metadata_file.exists():
        return
    try:
        active_metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        version = active_metadata.get("version", "unknown")
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        history_dir = active_path.parent / "forecast_history" / f"v{version}_{date_str}"
        history_dir.mkdir(parents=True, exist_ok=True)
        (history_dir / "metadata.json").write_text(
            json.dumps(active_metadata, indent=2), encoding="utf-8"
        )
        logger.info("forecaster_history_saved", version=version, path=str(history_dir))
    except Exception as exc:
        logger.warning("forecaster_history_save_error", error=str(exc))
