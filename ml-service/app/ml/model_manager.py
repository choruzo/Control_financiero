"""
Gestor del modelo DistilBERT para categorización de transacciones.

El ModelManager se inicializa en el lifespan de FastAPI y se inyecta en
app.state.model_manager. Los routers acceden a él via request.app.state.

Modo degradado: si el modelo no está entrenado/guardado en disco, el
manager devuelve ("Otros", 0.0) sin lanzar excepción, permitiendo que
el servicio arranque y responda siempre.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import structlog

from app.ml.categories import INDEX_TO_LABEL
from app.ml.preprocessor import normalize_banking_text

logger = structlog.get_logger(__name__)


class ModelManager:
    """Carga y gestiona el modelo de clasificación de transacciones."""

    def __init__(self, model_path: str, device: str = "cpu") -> None:
        self._model_path = Path(model_path)
        self._device = device
        self._model = None
        self._tokenizer = None
        self.loaded: bool = False
        self.metadata: dict = {}

    async def load(self) -> None:
        """
        Carga el modelo fine-tuned desde disco.

        Si el directorio del modelo no existe, el manager queda en modo
        degradado (loaded=False) y predict() devuelve confianza 0.
        """
        categorizer_path = self._model_path / "categorizer"
        if not categorizer_path.exists():
            logger.warning(
                "model_not_found",
                path=str(categorizer_path),
                message="Servicio en modo degradado. Ejecutar scripts/train.py para entrenar.",
            )
            return

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(str(categorizer_path))
            self._model = AutoModelForSequenceClassification.from_pretrained(
                str(categorizer_path)
            )
            self._model.to(self._device)
            self._model.eval()

            metadata_file = categorizer_path / "metadata.json"
            if metadata_file.exists():
                self.metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

            self.loaded = True
            logger.info(
                "model_loaded",
                version=self.metadata.get("version", "unknown"),
                device=self._device,
                accuracy=self.metadata.get("accuracy"),
            )
        except Exception as exc:
            logger.error("model_load_failed", error=str(exc))
            self.loaded = False

    def predict(self, description: str) -> tuple[str, float]:
        """
        Predice la categoría de una transacción bancaria.

        Returns:
            (category_name, confidence) — si no hay modelo cargado devuelve
            ("Otros", 0.0) para no interrumpir el flujo del backend.
        """
        if not self.loaded or self._model is None or self._tokenizer is None:
            return "Otros", 0.0

        try:
            import torch

            clean_text = normalize_banking_text(description)
            inputs = self._tokenizer(
                clean_text,
                return_tensors="pt",
                max_length=128,
                truncation=True,
                padding=True,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}

            with torch.no_grad():
                logits = self._model(**inputs).logits

            probs = torch.softmax(logits, dim=-1)[0]
            pred_idx = int(probs.argmax().item())
            confidence = float(probs[pred_idx].item())
            category_name = INDEX_TO_LABEL.get(pred_idx, "Otros")

            logger.debug(
                "prediction",
                description=description[:50],
                category=category_name,
                confidence=round(confidence, 4),
            )
            return category_name, confidence

        except Exception as exc:
            logger.error("prediction_failed", error=str(exc))
            return "Otros", 0.0

    def get_status(self) -> dict:
        """Devuelve el estado actual del modelo para el endpoint /model/status."""
        last_trained_raw = self.metadata.get("trained_at")
        last_trained: datetime | None = None
        if last_trained_raw:
            try:
                last_trained = datetime.fromisoformat(last_trained_raw)
            except ValueError:
                pass

        return {
            "loaded": self.loaded,
            "version": self.metadata.get("version"),
            "accuracy": self.metadata.get("accuracy"),
            "last_trained": last_trained,
            "feedback_count": 0,  # Fase 3.3: contar desde Redis
        }
