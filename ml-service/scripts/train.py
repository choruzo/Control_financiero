"""
Fine-tuning de DistilBERT multilingüe para categorización de transacciones.

Uso (dentro del contenedor o con venv activado):
    python scripts/train.py [--model-path /app/models] [--epochs 3] [--batch-size 16]

El script:
1. Carga data/dataset.json
2. Divide en train/val (80/20)
3. Fine-tunea distilbert-base-multilingual-cased (10 clases)
4. Evalúa accuracy en validación
5. Guarda modelo + tokenizer + metadata en {model_path}/categorizer/
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

# Asegurar que la raíz del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.trainer import (
    DATASET_PATH,
    BASE_MODEL,
    load_base_dataset,
    run_incremental_retrain,
    train_val_split,
)


def main(
    model_path: str,
    epochs: int,
    batch_size: int,
    device_override: str | None = None,
    extra_data_path: str | None = None,
) -> None:
    import json

    import torch

    device = device_override or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(f"Cargando dataset desde {DATASET_PATH}...")

    texts, labels = load_base_dataset()
    print(f"Ejemplos sintéticos: {len(texts)}")

    if extra_data_path:
        extra_path = Path(extra_data_path)
        if extra_path.exists():
            extra_data = json.loads(extra_path.read_text(encoding="utf-8"))
            from app.ml.categories import LABEL_TO_INDEX  # noqa: PLC0415

            added = 0
            for item in extra_data:
                label_name = item.get("label", "")
                if label_name in LABEL_TO_INDEX:
                    texts.append(item["text"])
                    labels.append(LABEL_TO_INDEX[label_name])
                    added += 1
            print(f"Ejemplos reales añadidos: {added}")
        else:
            print(f"AVISO: --extra-data {extra_data_path} no encontrado, ignorando.")

    print(f"Total ejemplos: {len(texts)}")
    counts = Counter(labels)
    print(f"Distribución de clases: {dict(sorted(counts.items()))}")

    train_texts, train_labels, val_texts, val_labels = train_val_split(texts, labels)
    print(f"Train: {len(train_texts)} | Val: {len(val_texts)}")

    # El entrenamiento inicial parte del BASE_MODEL de HuggingFace.
    # Pasamos una ruta inexistente para forzar el fallback a BASE_MODEL,
    # y current_version="0.9" para que la versión resultante sea "1.0".
    output_dir = Path(model_path) / "categorizer"
    print(f"Cargando modelo base '{BASE_MODEL}'...")

    metadata = run_incremental_retrain(
        source_model_path=Path(model_path) / "_initial_nonexistent",
        output_path=output_dir,
        feedback_items=[],
        epochs=epochs,
        batch_size=batch_size,
        device=device,
        current_version="0.9",
        train_texts=train_texts,
        train_labels=train_labels,
        val_texts=val_texts,
        val_labels=val_labels,
    )

    print(f"\nModelo guardado en {output_dir}")
    print(f"Best val accuracy: {metadata['accuracy']:.4f}")
    print(f"Metadata: {metadata}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tuning DistilBERT para categorización")
    parser.add_argument("--model-path", default="/app/models", help="Directorio de salida del modelo")
    parser.add_argument("--epochs", type=int, default=25, help="Número de epochs de entrenamiento")
    parser.add_argument("--batch-size", type=int, default=16, help="Tamaño del batch")
    parser.add_argument("--device", default=None, help="Device: cpu o cuda (auto-detecta si no se indica)")
    parser.add_argument("--extra-data", default=None, help="JSON con ejemplos reales adicionales")
    args = parser.parse_args()

    main(
        model_path=args.model_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        device_override=args.device,
        extra_data_path=args.extra_data,
    )
