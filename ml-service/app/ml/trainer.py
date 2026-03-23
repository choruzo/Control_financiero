"""
Módulo de entrenamiento incremental para el modelo de categorización.

Contiene la lógica compartida entre el entrenamiento inicial (scripts/train.py)
y el reentrenamiento incremental (routers/retrain.py).
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
import torch
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

from app.ml.categories import INDEX_TO_LABEL, LABEL_TO_INDEX, NUM_LABELS

logger = structlog.get_logger(__name__)

BASE_MODEL = "distilbert-base-multilingual-cased"
DATASET_PATH = Path(__file__).parent.parent.parent / "data" / "dataset.json"


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


def load_base_dataset(path: Path = DATASET_PATH) -> tuple[list[str], list[int]]:
    """Carga el dataset base de transacciones sintéticas."""
    data = json.loads(path.read_text(encoding="utf-8"))
    texts = [item["text"] for item in data]
    labels = [LABEL_TO_INDEX[item["label"]] for item in data]
    return texts, labels


def build_training_examples(
    feedback_items: list[dict],
    base_dataset_path: Path = DATASET_PATH,
) -> tuple[list[str], list[int]]:
    """
    Combina el dataset base con las correcciones del usuario.

    Args:
        feedback_items: Lista de dicts con {description, correct_category_id, ...}
        base_dataset_path: Ruta al dataset base JSON.

    Returns:
        (texts, labels) combinados del dataset base + feedback válido.
    """
    texts, labels = load_base_dataset(base_dataset_path)
    base_count = len(texts)

    feedback_count = 0
    for item in feedback_items:
        description = item.get("description", "").strip()
        correct_cat_id = item.get("correct_category_id")

        if not description:
            continue
        if correct_cat_id is None or int(correct_cat_id) not in INDEX_TO_LABEL:
            logger.warning("feedback_invalid_category", correct_category_id=correct_cat_id)
            continue

        texts.append(description)
        labels.append(int(correct_cat_id))
        feedback_count += 1

    logger.info(
        "training_examples_built",
        base=base_count,
        feedback=feedback_count,
        total=len(texts),
    )
    return texts, labels


def train_val_split(
    texts: list[str],
    labels: list[int],
    val_ratio: float = 0.2,
) -> tuple[list[str], list[int], list[str], list[int]]:
    """Split estratificado simple por clase."""
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
    """Calcula accuracy en el conjunto de validación."""
    model.eval()
    correct = total = 0
    with torch.no_grad():
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            batch_labels = batch["labels"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = outputs.logits.argmax(dim=-1)
            correct += (preds == batch_labels).sum().item()
            total += len(batch_labels)
    return correct / total if total > 0 else 0.0


def get_next_version(current_version: str) -> str:
    """
    Incrementa el minor de la versión semántica simple.

    Ejemplos: "1.0" -> "1.1", "1.9" -> "1.10", "2.3" -> "2.4"
    """
    try:
        major, minor = current_version.split(".", 1)
        return f"{major}.{int(minor) + 1}"
    except (ValueError, AttributeError):
        return "1.1"


def run_incremental_retrain(
    source_model_path: Path,
    output_path: Path,
    feedback_items: list[dict],
    epochs: int = 2,
    batch_size: int = 16,
    device: str = "cpu",
    base_dataset_path: Path = DATASET_PATH,
    current_version: str = "1.0",
    train_texts: list[str] | None = None,
    train_labels: list[int] | None = None,
    val_texts: list[str] | None = None,
    val_labels: list[int] | None = None,
) -> dict:
    """
    Ejecuta reentrenamiento incremental del modelo.

    Parte del modelo activo (source_model_path) para preservar el conocimiento
    previo. Si el modelo activo no existe, cae back al BASE_MODEL de HuggingFace.

    Si se proporcionan train_texts/train_labels/val_texts/val_labels, se usan
    directamente en lugar de construir el dataset internamente.

    Args:
        source_model_path: Directorio del modelo activo (punto de partida).
        output_path: Directorio donde guardar el modelo candidato.
        feedback_items: Correcciones del usuario desde Redis.
        epochs: Número de epochs de fine-tuning incremental.
        batch_size: Tamaño de batch.
        device: "cpu" o "cuda".
        base_dataset_path: Dataset base sintético.
        current_version: Versión del modelo activo para calcular la nueva.
        train_texts: Textos de entrenamiento pre-construidos (opcional).
        train_labels: Etiquetas de entrenamiento pre-construidas (opcional).
        val_texts: Textos de validación pre-construidos (opcional).
        val_labels: Etiquetas de validación pre-construidas (opcional).

    Returns:
        dict con: version, accuracy, train_examples, val_examples, trained_at, device

    Raises:
        Exception: Si el entrenamiento falla.
    """
    if source_model_path.exists():
        model_source = str(source_model_path)
        logger.info("retrain_source", source="active_model", path=model_source)
    else:
        model_source = BASE_MODEL
        logger.warning("retrain_source", source="base_model", reason="active model not found")

    if train_texts is None or train_labels is None or val_texts is None or val_labels is None:
        texts, labels = build_training_examples(feedback_items, base_dataset_path)
        train_texts, train_labels, val_texts, val_labels = train_val_split(texts, labels)

    logger.info(
        "retrain_start",
        train=len(train_texts),
        val=len(val_texts),
        epochs=epochs,
        device=device,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_source)
    train_ds = TransactionDataset(train_texts, train_labels, tokenizer)
    val_ds = TransactionDataset(val_texts, val_labels, tokenizer)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    model = AutoModelForSequenceClassification.from_pretrained(model_source, num_labels=NUM_LABELS)
    model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(1, total_steps // 10),
        num_training_steps=total_steps,
    )

    best_accuracy = 0.0
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            batch_labels = batch["labels"].to(device)

            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=batch_labels)
            outputs.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += outputs.loss.item()

        accuracy = evaluate(model, val_loader, device)
        logger.info(
            "retrain_epoch",
            epoch=epoch,
            epochs=epochs,
            val_accuracy=round(accuracy, 4),
            avg_loss=round(total_loss / max(len(train_loader), 1), 4),
        )
        if accuracy > best_accuracy:
            best_accuracy = accuracy

    output_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_path))
    tokenizer.save_pretrained(str(output_path))

    new_version = get_next_version(current_version)
    metadata = {
        "version": new_version,
        "base_model": BASE_MODEL,
        "num_labels": NUM_LABELS,
        "epochs": epochs,
        "batch_size": batch_size,
        "accuracy": round(best_accuracy, 4),
        "train_examples": len(train_texts),
        "val_examples": len(val_texts),
        "trained_at": datetime.now(UTC).isoformat(),
        "device": device,
        "feedback_incorporated": len(feedback_items),
    }
    (output_path / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    logger.info(
        "retrain_complete",
        version=new_version,
        accuracy=round(best_accuracy, 4),
        output=str(output_path),
    )
    return metadata
