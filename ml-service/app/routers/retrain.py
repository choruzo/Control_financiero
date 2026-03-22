"""
Router de reentrenamiento incremental del modelo.

Expone POST /retrain para que el backend Celery dispare el ciclo de reentrenamiento.
El entrenamiento se ejecuta en un ThreadPoolExecutor para no bloquear el event loop de
FastAPI, ya que PyTorch es CPU/GPU-bound y no libera el GIL durante el entrenamiento.

Flujo:
1. Verificar que no haya reentrenamiento en curso (409 si sí).
2. Leer feedback pendiente de Redis.
3. Si hay menos de min_feedback_for_retrain entradas, omitir (200 skipped).
4. Lanzar reentrenamiento en ThreadPoolExecutor y devolver 202 inmediatamente.
5. Callback async: promover candidato si accuracy mejora, descartar si empeora.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.ml.trainer import run_incremental_retrain
from app.schemas.retrain import RetrainResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/retrain", tags=["retrain"])

FEEDBACK_KEY = "ml:feedback"

# ThreadPoolExecutor dedicado al entrenamiento (máximo 1 tarea simultánea)
_retrain_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="retrain")


@router.post("", response_model=RetrainResponse)
async def trigger_retrain(req: Request):
    """
    Dispara un ciclo de reentrenamiento incremental.

    Respuestas:
    - **202**: Reentrenamiento iniciado en background.
    - **200**: Feedback insuficiente, reentrenamiento omitido.
    - **409**: Ya hay un reentrenamiento en curso.
    - **503**: Redis no disponible.
    """
    # Verificar concurrencia
    if getattr(req.app.state, "retrain_in_progress", False):
        return JSONResponse(
            status_code=409,
            content={
                "status": "in_progress",
                "feedback_count": 0,
                "reason": "Reentrenamiento ya en curso",
                "model_version": None,
            },
        )

    # Leer feedback de Redis
    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        raw_items = await redis.lrange(FEEDBACK_KEY, 0, -1)
        await redis.aclose()
    except Exception as exc:
        logger.warning("retrain_redis_error", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "feedback_count": 0,
                "reason": f"Redis no disponible: {exc}",
                "model_version": None,
            },
        )

    feedback_count = len(raw_items)

    if feedback_count < settings.min_feedback_for_retrain:
        logger.info(
            "retrain_skipped",
            feedback_count=feedback_count,
            min_required=settings.min_feedback_for_retrain,
        )
        return JSONResponse(
            status_code=200,
            content={
                "status": "skipped",
                "feedback_count": feedback_count,
                "reason": f"Feedback insuficiente (mínimo: {settings.min_feedback_for_retrain})",
                "model_version": None,
            },
        )

    # Parsear feedback
    feedback_items = []
    for raw in raw_items:
        try:
            feedback_items.append(json.loads(raw))
        except json.JSONDecodeError:
            continue

    # Marcar como en progreso y capturar estado del contexto
    req.app.state.retrain_in_progress = True
    source_path = Path(settings.model_path) / "categorizer"
    candidate_path = Path(settings.model_path) / "categorizer_candidate"
    current_version = req.app.state.model_manager.metadata.get("version", "1.0")
    app = req.app
    loop = asyncio.get_running_loop()

    def _run_sync() -> None:
        """Función síncrona que corre en el ThreadPoolExecutor."""
        try:
            metadata = run_incremental_retrain(
                source_model_path=source_path,
                output_path=candidate_path,
                feedback_items=feedback_items,
                epochs=settings.retrain_epochs,
                batch_size=settings.retrain_batch_size,
                device=settings.device,
                current_version=current_version,
            )
            asyncio.run_coroutine_threadsafe(
                _on_retrain_complete(app, metadata, success=True),
                loop,
            )
        except Exception as exc:
            logger.error("retrain_thread_failed", error=str(exc))
            asyncio.run_coroutine_threadsafe(
                _on_retrain_complete(app, {}, success=False),
                loop,
            )

    loop.run_in_executor(_retrain_executor, _run_sync)

    logger.info("retrain_started", feedback_count=feedback_count, version=current_version)
    return JSONResponse(
        status_code=202,
        content={
            "status": "started",
            "feedback_count": feedback_count,
            "reason": None,
            "model_version": current_version,
        },
    )


async def _on_retrain_complete(app, metadata: dict, success: bool) -> None:
    """Callback async ejecutado en el event loop tras completar el training en el thread."""
    try:
        if not success:
            logger.error("retrain_failed_cleaning_up")
            return

        candidate_path = Path(settings.model_path) / "categorizer_candidate"
        active_path = Path(settings.model_path) / "categorizer"

        candidate_accuracy = metadata.get("accuracy", 0.0)
        active_accuracy = app.state.model_manager.metadata.get("accuracy", 0.0)

        # Tolerancia del 2% para variabilidad estadística en conjuntos de validación pequeños
        if candidate_accuracy >= active_accuracy - 0.02:
            # PROMOVER: backup metadata activa, mover candidato a producción
            _backup_active_metadata(active_path)

            if candidate_path.exists():
                if active_path.exists():
                    shutil.rmtree(str(active_path))
                shutil.move(str(candidate_path), str(active_path))

            await app.state.model_manager.reload()

            # Archivar feedback procesado en Redis
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            try:
                redis = aioredis.from_url(settings.redis_url, decode_responses=True)
                await redis.rename(FEEDBACK_KEY, f"ml:feedback:processed_{timestamp}")
                await redis.aclose()
            except Exception as exc:
                logger.warning("retrain_redis_cleanup_error", error=str(exc))

            logger.info(
                "model_promoted",
                new_version=metadata.get("version"),
                new_accuracy=candidate_accuracy,
                old_accuracy=active_accuracy,
            )
        else:
            # DESCARTAR candidato
            if candidate_path.exists():
                shutil.rmtree(str(candidate_path))
            logger.warning(
                "model_rejected",
                candidate_accuracy=candidate_accuracy,
                active_accuracy=active_accuracy,
                margin=round(active_accuracy - candidate_accuracy, 4),
            )
    finally:
        app.state.retrain_in_progress = False


def _backup_active_metadata(active_path: Path) -> None:
    """Copia el metadata del modelo activo al historial antes de sobrescribirlo."""
    metadata_file = active_path / "metadata.json"
    if not metadata_file.exists():
        return
    try:
        active_metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        version = active_metadata.get("version", "unknown")
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        history_dir = active_path.parent / "history" / f"v{version}_{date_str}"
        history_dir.mkdir(parents=True, exist_ok=True)
        (history_dir / "metadata.json").write_text(
            json.dumps(active_metadata, indent=2), encoding="utf-8"
        )
        logger.info("model_history_saved", version=version, path=str(history_dir))
    except Exception as exc:
        logger.warning("model_history_save_error", error=str(exc))
