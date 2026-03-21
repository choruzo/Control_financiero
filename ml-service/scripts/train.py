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
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Asegurar que la raíz del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from app.ml.categories import LABEL_TO_INDEX, NUM_LABELS

BASE_MODEL = "distilbert-base-multilingual-cased"
DATASET_PATH = Path(__file__).parent.parent / "data" / "dataset.json"


class TransactionDataset(Dataset):
    def __init__(self, texts: list[str], labels: list[int], tokenizer: Any, max_length: int = 128) -> None:
        self.encodings = tokenizer(
            texts,
            max_length=max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict:
        return {
            "input_ids": self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "labels": self.labels[idx],
        }


def load_dataset(path: Path) -> tuple[list[str], list[int]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    texts = [item["text"] for item in data]
    labels = [LABEL_TO_INDEX[item["label"]] for item in data]
    return texts, labels


def train_val_split(
    texts: list[str],
    labels: list[int],
    val_ratio: float = 0.2,
) -> tuple[list[str], list[int], list[str], list[int]]:
    """Split estratificado simple por clase."""
    from collections import defaultdict
    import random

    random.seed(42)
    by_class: dict[int, list[int]] = defaultdict(list)
    for i, label in enumerate(labels):
        by_class[label].append(i)

    train_idx, val_idx = [], []
    for indices in by_class.values():
        random.shuffle(indices)
        split = max(1, int(len(indices) * val_ratio))
        val_idx.extend(indices[:split])
        train_idx.extend(indices[split:])

    return (
        [texts[i] for i in train_idx],
        [labels[i] for i in train_idx],
        [texts[i] for i in val_idx],
        [labels[i] for i in val_idx],
    )


def evaluate(model: Any, loader: DataLoader, device: str) -> float:
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = outputs.logits.argmax(dim=-1)
            correct += (preds == labels).sum().item()
            total += len(labels)
    return correct / total if total > 0 else 0.0


def main(model_path: str, epochs: int, batch_size: int) -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    print(f"Cargando dataset desde {DATASET_PATH}...")

    texts, labels = load_dataset(DATASET_PATH)
    print(f"Total ejemplos: {len(texts)}")
    counts = Counter(labels)
    print(f"Distribución de clases: {dict(sorted(counts.items()))}")

    train_texts, train_labels, val_texts, val_labels = train_val_split(texts, labels)
    print(f"Train: {len(train_texts)} | Val: {len(val_texts)}")

    print(f"Cargando tokenizer '{BASE_MODEL}'...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    train_ds = TransactionDataset(train_texts, train_labels, tokenizer)
    val_ds = TransactionDataset(val_texts, val_labels, tokenizer)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    print(f"Cargando modelo '{BASE_MODEL}' con {NUM_LABELS} clases...")
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL, num_labels=NUM_LABELS
    )
    model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=total_steps // 10, num_training_steps=total_steps
    )

    best_accuracy = 0.0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for step, batch in enumerate(train_loader, 1):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            batch_labels = batch["labels"].to(device)

            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=batch_labels)
            loss = outputs.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

            if step % 5 == 0 or step == len(train_loader):
                print(f"  Epoch {epoch}/{epochs} | Step {step}/{len(train_loader)} | Loss: {total_loss/step:.4f}")

        accuracy = evaluate(model, val_loader, device)
        print(f"Epoch {epoch} finalizado. Val accuracy: {accuracy:.4f}")
        if accuracy > best_accuracy:
            best_accuracy = accuracy

    # Guardar modelo
    output_dir = Path(model_path) / "categorizer"
    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    metadata = {
        "version": "1.0",
        "base_model": BASE_MODEL,
        "num_labels": NUM_LABELS,
        "epochs": epochs,
        "batch_size": batch_size,
        "accuracy": round(best_accuracy, 4),
        "train_examples": len(train_texts),
        "val_examples": len(val_texts),
        "trained_at": datetime.now(UTC).isoformat(),
        "device": device,
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(f"\nModelo guardado en {output_dir}")
    print(f"Best val accuracy: {best_accuracy:.4f}")
    print(f"Metadata: {metadata}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tuning DistilBERT para categorización")
    parser.add_argument("--model-path", default="/app/models", help="Directorio de salida del modelo")
    parser.add_argument("--epochs", type=int, default=3, help="Número de epochs de entrenamiento")
    parser.add_argument("--batch-size", type=int, default=16, help="Tamaño del batch")
    args = parser.parse_args()

    main(model_path=args.model_path, epochs=args.epochs, batch_size=args.batch_size)
