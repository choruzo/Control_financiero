"""
Gestor del modelo LSTM para predicción de flujo de caja.

Sigue el mismo patrón que ModelManager (categorización):
- Modo degradado si no hay modelo en disco
- Prophet como fallback estadístico cuando el LSTM no está cargado
- MC Dropout para generar intervalos de confianza (P10/P50/P90)

El Forecaster se inicializa en el lifespan de FastAPI y se accede via
app.state.forecaster desde los routers.
"""

from __future__ import annotations

import json
import pickle
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

SEQ_LEN = 12  # Meses de historial usados como input del LSTM


class Forecaster:
    """Carga y gestiona el modelo LSTM de predicción de cashflow."""

    def __init__(self, model_path: str, device: str = "cpu") -> None:
        self._model_path = Path(model_path) / "forecaster"
        self._device = device
        self._model = None
        self._scaler = None
        self.loaded: bool = False
        self.metadata: dict = {}

    async def load(self) -> None:
        """
        Carga el modelo LSTM desde disco.

        Si el directorio no existe, queda en modo degradado (loaded=False)
        y predict() usará Prophet o respuesta vacía.
        """
        if not self._model_path.exists():
            logger.warning(
                "forecaster_not_found",
                path=str(self._model_path),
                message="Forecaster en modo degradado. Ejecutar scripts/train_forecaster.py.",
            )
            return

        try:
            import torch

            from app.ml.lstm_model import CashflowLSTM

            model_file = self._model_path / "model.pt"
            scaler_file = self._model_path / "scaler.pkl"
            metadata_file = self._model_path / "metadata.json"

            if not model_file.exists():
                logger.warning("forecaster_model_file_missing", path=str(model_file))
                return

            self._model = CashflowLSTM()
            self._model.load_state_dict(
                torch.load(str(model_file), map_location=self._device, weights_only=True)
            )
            self._model.to(self._device)
            self._model.eval()

            if scaler_file.exists():
                with open(scaler_file, "rb") as f:
                    self._scaler = pickle.load(f)  # noqa: S301

            if metadata_file.exists():
                self.metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

            self.loaded = True
            logger.info(
                "forecaster_loaded",
                version=self.metadata.get("version", "unknown"),
                device=self._device,
                mae=self.metadata.get("mae"),
            )
        except Exception as exc:
            logger.error("forecaster_load_failed", error=str(exc))
            self.loaded = False

    def predict(
        self,
        historical_data: list[dict],
        months_ahead: int,
        n_samples: int = 50,
    ) -> tuple[list[dict], str]:
        """
        Predice el cashflow para los próximos N meses.

        Args:
            historical_data: Lista de dicts con year, month, income, expenses
            months_ahead: Meses a predecir (1-12)
            n_samples: Muestras MC Dropout para intervalos de confianza

        Returns:
            (predictions, model_used) donde model_used es "lstm", "prophet" o "degraded"
        """
        if self.loaded and self._model is not None:
            try:
                result = self._predict_lstm(historical_data, months_ahead, n_samples)
                return result, "lstm"
            except Exception as exc:
                logger.error("lstm_predict_failed_falling_back", error=str(exc))

        # Fallback a Prophet
        try:
            result = self._predict_prophet(historical_data, months_ahead)
            return result, "prophet"
        except Exception as exc:
            logger.warning("prophet_fallback_failed", error=str(exc))

        return self._degraded_response(historical_data, months_ahead), "degraded"

    def _predict_lstm(
        self, historical_data: list[dict], months_ahead: int, n_samples: int
    ) -> list[dict]:
        import torch

        data = np.array(
            [[float(d["income"]), float(d["expenses"])] for d in historical_data],
            dtype=np.float32,
        )

        # Normalizar con el scaler entrenado
        if self._scaler is not None:
            data_scaled = self._scaler.transform(data).astype(np.float32)
        else:
            data_scaled = data.copy()

        # Preparar secuencia inicial (últimos SEQ_LEN meses; pad si hay menos)
        if len(data_scaled) < SEQ_LEN:
            pad_size = SEQ_LEN - len(data_scaled)
            pad = np.tile(data_scaled[0:1], (pad_size, 1)).astype(np.float32)
            seq = np.vstack([pad, data_scaled])
        else:
            seq = data_scaled[-SEQ_LEN:]

        # MC Dropout: activar modo train para que el dropout funcione en inferencia
        self._model.train()
        all_predictions: list[np.ndarray] = []
        try:
            for _ in range(n_samples):
                current_seq = seq.copy()
                sample_preds: list[np.ndarray] = []

                for _ in range(months_ahead):
                    x = torch.tensor(
                        current_seq[-SEQ_LEN:], dtype=torch.float32
                    ).unsqueeze(0).to(self._device)

                    with torch.no_grad():
                        pred = self._model(x).cpu().numpy()[0]

                    sample_preds.append(pred.copy())
                    # Rolling window: añadir predicción como próximo input
                    current_seq = np.vstack([current_seq[1:], pred])

                all_predictions.append(np.array(sample_preds))
        finally:
            self._model.eval()  # Siempre restaurar modo eval

        # all_predictions: [n_samples, months_ahead, 2]
        all_preds_arr = np.array(all_predictions)

        # Desnormalizar y clipear a valores no negativos
        if self._scaler is not None:
            shape = all_preds_arr.shape
            flat = all_preds_arr.reshape(-1, 2)
            flat_denorm = self._scaler.inverse_transform(flat).astype(np.float32)
            flat_denorm = np.maximum(flat_denorm, 0.0)
            all_preds_arr = flat_denorm.reshape(shape)
        else:
            all_preds_arr = np.maximum(all_preds_arr, 0.0)

        # Percentiles
        p10 = np.percentile(all_preds_arr, 10, axis=0)
        p50 = np.percentile(all_preds_arr, 50, axis=0)
        p90 = np.percentile(all_preds_arr, 90, axis=0)

        return self._build_result(self._next_months(historical_data, months_ahead), p10, p50, p90)

    def _predict_prophet(self, historical_data: list[dict], months_ahead: int) -> list[dict]:
        """Fallback estadístico usando Prophet."""
        try:
            import pandas as pd
            from prophet import Prophet
        except ImportError as exc:
            raise RuntimeError("Prophet no está instalado") from exc

        if len(historical_data) < 3:
            raise ValueError("Datos insuficientes para Prophet (mínimo 3 meses)")

        future_months = self._next_months(historical_data, months_ahead)
        future_dates = pd.to_datetime(
            [f"{y}-{mo:02d}-01" for y, mo in future_months]
        )

        def _fit_prophet(values: list[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
            df = pd.DataFrame({
                "ds": pd.to_datetime(
                    [f"{d['year']}-{d['month']:02d}-01" for d in historical_data]
                ),
                "y": values,
            })
            m = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=0.8,
            )
            m.fit(df)
            forecast = m.predict(pd.DataFrame({"ds": future_dates}))
            yhat_lower = np.maximum(forecast["yhat_lower"].values, 0.0)
            yhat = np.maximum(forecast["yhat"].values, 0.0)
            yhat_upper = np.maximum(forecast["yhat_upper"].values, 0.0)
            return yhat_lower, yhat, yhat_upper

        inc_p10_arr, inc_p50_arr, inc_p90_arr = _fit_prophet(
            [float(d["income"]) for d in historical_data]
        )
        exp_p10_arr, exp_p50_arr, exp_p90_arr = _fit_prophet(
            [float(d["expenses"]) for d in historical_data]
        )

        # Construir resultado en formato compatible con _build_result
        p10 = np.column_stack([inc_p10_arr, exp_p10_arr])
        p50 = np.column_stack([inc_p50_arr, exp_p50_arr])
        p90 = np.column_stack([inc_p90_arr, exp_p90_arr])

        return self._build_result(future_months, p10, p50, p90)

    @staticmethod
    def _build_result(
        future_months: list[tuple[int, int]],
        p10: np.ndarray,
        p50: np.ndarray,
        p90: np.ndarray,
    ) -> list[dict]:
        result = []
        for i, (y, m) in enumerate(future_months):
            inc_p10 = round(float(p10[i, 0]), 2)
            inc_p50 = round(float(p50[i, 0]), 2)
            inc_p90 = round(float(p90[i, 0]), 2)
            exp_p10 = round(float(p10[i, 1]), 2)
            exp_p50 = round(float(p50[i, 1]), 2)
            exp_p90 = round(float(p90[i, 1]), 2)
            result.append({
                "year": y,
                "month": m,
                "income_p10": inc_p10,
                "income_p50": inc_p50,
                "income_p90": inc_p90,
                "expenses_p10": exp_p10,
                "expenses_p50": exp_p50,
                "expenses_p90": exp_p90,
                # net_p10 = pesimista (poco ingreso, mucho gasto)
                "net_p10": round(inc_p10 - exp_p90, 2),
                "net_p50": round(inc_p50 - exp_p50, 2),
                "net_p90": round(inc_p90 - exp_p10, 2),
            })
        return result

    @staticmethod
    def _degraded_response(
        historical_data: list[dict], months_ahead: int
    ) -> list[dict]:
        """Respuesta vacía cuando no hay modelo ni Prophet disponible."""
        future_months = Forecaster._next_months(historical_data, months_ahead)
        return [
            {
                "year": y, "month": m,
                "income_p10": 0.0, "income_p50": 0.0, "income_p90": 0.0,
                "expenses_p10": 0.0, "expenses_p50": 0.0, "expenses_p90": 0.0,
                "net_p10": 0.0, "net_p50": 0.0, "net_p90": 0.0,
            }
            for y, m in future_months
        ]

    @staticmethod
    def _next_months(historical_data: list[dict], n: int) -> list[tuple[int, int]]:
        """Genera los N meses siguientes al último dato histórico."""
        if not historical_data:
            today = datetime.now(UTC).date()
            last_y, last_m = today.year, today.month
        else:
            last = historical_data[-1]
            last_y, last_m = int(last["year"]), int(last["month"])

        months: list[tuple[int, int]] = []
        y, m = last_y, last_m
        for _ in range(n):
            m += 1
            if m > 12:
                m = 1
                y += 1
            months.append((y, m))
        return months

    async def reload(self) -> None:
        """Recarga el modelo desde disco tras un reentrenamiento exitoso."""
        self._model = None
        self._scaler = None
        self.loaded = False
        self.metadata = {}
        await self.load()
        logger.info("forecaster_reloaded", loaded=self.loaded, version=self.metadata.get("version"))

    def get_status(self) -> dict:
        """Devuelve el estado actual del forecaster."""
        last_trained_raw = self.metadata.get("trained_at")
        last_trained: str | None = None
        if last_trained_raw:
            try:
                last_trained = datetime.fromisoformat(last_trained_raw).isoformat()
            except ValueError:
                pass

        return {
            "loaded": self.loaded,
            "version": self.metadata.get("version"),
            "mae": self.metadata.get("mae"),
            "last_trained": last_trained,
        }
