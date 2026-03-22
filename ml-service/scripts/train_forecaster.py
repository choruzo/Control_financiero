"""
Script de entrenamiento inicial del modelo LSTM de forecasting.

Genera (o carga) un dataset sintético de series temporales y entrena el modelo.

Uso dentro del contenedor:
    python scripts/train_forecaster.py
    python scripts/train_forecaster.py --epochs 30 --output /app/models
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

# Añadir la raíz del proyecto al path para importar app.*
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.lstm_model import CashflowLSTM  # noqa: E402

SEQ_LEN = 12


def build_windows(
    series_list: list[list[list[float]]],
) -> tuple[np.ndarray, np.ndarray]:
    """Crea ventanas deslizantes (SEQ_LEN → siguiente mes) de todas las series."""
    X_list: list[np.ndarray] = []
    y_list: list[np.ndarray] = []

    for series in series_list:
        arr = np.array(series, dtype=np.float32)
        for i in range(len(arr) - SEQ_LEN):
            X_list.append(arr[i : i + SEQ_LEN])
            y_list.append(arr[i + SEQ_LEN])

    if not X_list:
        raise ValueError("No se generaron ejemplos. Verifica que las series tengan > 12 meses.")

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.float32)


def train(
    dataset: list[list[list[float]]],
    output_path: Path,
    epochs: int = 20,
    batch_size: int = 32,
    device: str = "cpu",
    lr: float = 1e-3,
) -> dict:
    """
    Entrena el modelo LSTM y guarda artefactos en output_path.

    Returns:
        Metadata del modelo entrenado.
    """
    print(f"Preparando dataset: {len(dataset)} series...")
    X, y = build_windows(dataset)
    print(f"  Ejemplos de entrenamiento: {len(X)}")

    # Normalizar
    all_values = np.vstack([X.reshape(-1, 2), y])
    scaler = StandardScaler()
    scaler.fit(all_values)

    X_scaled = scaler.transform(X.reshape(-1, 2)).reshape(X.shape).astype(np.float32)
    y_scaled = scaler.transform(y).astype(np.float32)

    # Split 80/20
    n = len(X_scaled)
    split = int(n * 0.8)
    X_train, X_val = X_scaled[:split], X_scaled[split:]
    y_train, y_val = y_scaled[:split], y_scaled[split:]
    print(f"  Train: {len(X_train)} | Val: {len(X_val)}")

    # DataLoader
    train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    # Modelo
    model = CashflowLSTM()
    model.to(device)
    model.train()

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    print(f"\nEntrenando {epochs} epochs en {device}...")
    best_val_loss = float("inf")

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            pred = model(xb)
            loss = criterion(pred, yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item()

        scheduler.step()
        avg_loss = total_loss / max(len(train_loader), 1)

        if epoch % 5 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d}/{epochs} | Loss: {avg_loss:.6f}")

        if avg_loss < best_val_loss:
            best_val_loss = avg_loss

    # Evaluación final en validación
    model.eval()
    mae = float("inf")
    if len(X_val) > 0:
        X_val_t = torch.from_numpy(X_val).to(device)
        with torch.no_grad():
            y_pred_scaled = model(X_val_t).cpu().numpy()
        y_pred = scaler.inverse_transform(y_pred_scaled)
        y_true = scaler.inverse_transform(y_val)
        mae = float(np.mean(np.abs(y_pred - y_true)))
        mae_income = float(np.mean(np.abs(y_pred[:, 0] - y_true[:, 0])))
        mae_expenses = float(np.mean(np.abs(y_pred[:, 1] - y_true[:, 1])))
        print(f"\nMAE validación: {mae:.2f}€ (ingresos: {mae_income:.2f}€, gastos: {mae_expenses:.2f}€)")

    # Guardar artefactos
    output_path.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(output_path / "model.pt"))
    with open(output_path / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    metadata = {
        "version": "1.0",
        "mae": round(mae, 4),
        "trained_at": datetime.now(UTC).isoformat(),
        "training_series": len(dataset),
        "training_examples": len(X_train),
        "epochs": epochs,
        "device": device,
    }
    (output_path / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(f"\nModelo guardado en: {output_path}")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrenar modelo LSTM de forecasting")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--output", type=str, default="/app/models/forecaster")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(Path(__file__).parent.parent / "data" / "timeseries_dataset.json"),
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if dataset_path.exists():
        print(f"Cargando dataset desde {dataset_path}...")
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    else:
        print("Dataset no encontrado. Generando dataset sintético...")
        # Añadir ruta de data/ para importar generate_timeseries
        data_dir = Path(__file__).parent.parent / "data"
        sys.path.insert(0, str(data_dir))
        from generate_timeseries import generate_dataset  # noqa: E402

        dataset = generate_dataset()
        dataset_path.parent.mkdir(parents=True, exist_ok=True)
        dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
        print(f"Dataset guardado en {dataset_path}")

    metadata = train(
        dataset=dataset,
        output_path=Path(args.output),
        epochs=args.epochs,
        batch_size=args.batch_size,
        device=args.device,
    )
    print(f"\nEntrenamiento completado. MAE: {metadata['mae']:.4f}€")


if __name__ == "__main__":
    main()
