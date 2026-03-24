"""
Diagnostico completo del modelo DistilBERT entrenado.

Detecta overfitting / underfitting comparando:
  - Accuracy train vs val
  - Metricas por categoria (precision, recall, F1)
  - Distribucion de confianza (umbral 0.92 / 0.5)
  - Ejemplos reales mal clasificados

Uso (dentro del contenedor):
    python scripts/eval_model.py
    python scripts/eval_model.py --model-path /app/models --epochs-log
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

from app.ml.categories import INDEX_TO_LABEL, LABEL_TO_INDEX
from app.ml.trainer import (
    TransactionDataset,
    load_base_dataset,
    train_val_split,
)
from transformers import AutoModelForSequenceClassification, AutoTokenizer


# ── Metricas por clase ────────────────────────────────────────────────────────

def compute_per_class_metrics(
    preds: list[int], targets: list[int], num_classes: int
) -> dict:
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)

    for p, t in zip(preds, targets):
        if p == t:
            tp[t] += 1
        else:
            fp[p] += 1
            fn[t] += 1

    metrics = {}
    for c in range(num_classes):
        precision = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) > 0 else 0.0
        recall    = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        metrics[c] = {"precision": precision, "recall": recall, "f1": f1, "tp": tp[c], "fp": fp[c], "fn": fn[c]}

    return metrics


def evaluate_with_probs(
    model, loader: DataLoader, device: str
) -> tuple[list[int], list[int], list[float]]:
    model.eval()
    all_preds, all_targets, all_confs = [], [], []
    with torch.no_grad():
        for batch in loader:
            input_ids      = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels         = batch["labels"].to(device)
            outputs        = model(input_ids=input_ids, attention_mask=attention_mask)
            probs          = F.softmax(outputs.logits, dim=-1)
            preds          = probs.argmax(dim=-1)
            confs          = probs.max(dim=-1).values
            all_preds.extend(preds.cpu().tolist())
            all_targets.extend(labels.cpu().tolist())
            all_confs.extend(confs.cpu().tolist())
    return all_preds, all_targets, all_confs


def accuracy(preds: list[int], targets: list[int]) -> float:
    return sum(p == t for p, t in zip(preds, targets)) / len(targets)


# ── Main ──────────────────────────────────────────────────────────────────────

def main(model_path: str) -> None:
    model_dir = Path(model_path) / "categorizer"
    if not model_dir.exists():
        print(f"[ERROR] Modelo no encontrado en {model_dir}")
        print("  Ejecuta primero: python scripts/train.py")
        sys.exit(1)

    # Metadata guardada
    meta_path = model_dir / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        print("\n=== METADATA DEL MODELO ===")
        print(f"  Version          : {meta.get('version')}")
        print(f"  Epochs entrenado : {meta.get('epochs')}")
        print(f"  Train examples   : {meta.get('train_examples')}")
        print(f"  Val examples     : {meta.get('val_examples')}")
        print(f"  Val accuracy     : {meta.get('accuracy', 0)*100:.1f}%")
        print(f"  Entrenado        : {meta.get('trained_at')}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nDevice: {device}")
    print(f"Cargando modelo desde {model_dir}...")

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model     = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    model.to(device)

    # Dataset completo
    texts, labels = load_base_dataset()
    random.seed(42)
    train_texts, train_labels, val_texts, val_labels = train_val_split(texts, labels)

    print(f"Dataset: {len(texts)} total | {len(train_texts)} train | {len(val_texts)} val")

    # DataLoaders
    train_ds = TransactionDataset(train_texts, train_labels, tokenizer)
    val_ds   = TransactionDataset(val_texts,   val_labels,   tokenizer)
    train_loader = DataLoader(train_ds, batch_size=32)
    val_loader   = DataLoader(val_ds,   batch_size=32)

    # Evaluar en TRAIN
    print("\nEvaluando en train...")
    train_preds, train_targets, train_confs = evaluate_with_probs(model, train_loader, device)
    train_acc = accuracy(train_preds, train_targets)

    # Evaluar en VAL
    print("Evaluando en val...")
    val_preds, val_targets, val_confs = evaluate_with_probs(model, val_loader, device)
    val_acc = accuracy(val_preds, val_targets)

    gap = train_acc - val_acc

    # ── Diagnostico overfitting / underfitting ────────────────────────────────
    print("\n" + "=" * 60)
    print("  DIAGNOSTICO OVERFITTING / UNDERFITTING")
    print("=" * 60)
    print(f"  Train accuracy : {train_acc*100:.2f}%")
    print(f"  Val   accuracy : {val_acc*100:.2f}%")
    print(f"  GAP (train-val): {gap*100:.2f}%")
    print("-" * 60)

    if train_acc < 0.70:
        print("  [UNDERFITTING] El modelo no aprende bien el dataset.")
        print("  -> Aumenta epochs, reduce dropout, usa lr mas alta.")
    elif gap > 0.15:
        print("  [OVERFITTING SEVERO] GAP > 15%.")
        print("  -> Reduce epochs, aumenta dropout, mas datos o data augmentation.")
    elif gap > 0.08:
        print("  [OVERFITTING LEVE] GAP entre 8-15%.")
        print("  -> Considera reducir epochs o anadir regularizacion.")
    elif train_acc >= 0.90 and val_acc >= 0.85:
        print("  [BUEN AJUSTE] El modelo generaliza correctamente.")
    else:
        print("  [AJUSTE ACEPTABLE] Margen de mejora disponible.")

    # ── Metricas por categoria ────────────────────────────────────────────────
    num_classes = len(INDEX_TO_LABEL)
    val_metrics = compute_per_class_metrics(val_preds, val_targets, num_classes)

    print("\n" + "=" * 60)
    print("  METRICAS POR CATEGORIA (validacion)")
    print("=" * 60)
    print(f"  {'Categoria':<25} {'Prec':>6} {'Recall':>7} {'F1':>6} {'TP':>4} {'FP':>4} {'FN':>4}")
    print("-" * 60)

    low_f1_categories = []
    for idx, name in sorted(INDEX_TO_LABEL.items()):
        m = val_metrics[idx]
        flag = ""
        if m["f1"] < 0.70:
            flag = " <-- bajo"
            low_f1_categories.append(name)
        print(
            f"  {name:<25} {m['precision']:>5.1%} {m['recall']:>6.1%} "
            f"{m['f1']:>5.1%} {m['tp']:>4} {m['fp']:>4} {m['fn']:>4}{flag}"
        )

    # ── Distribucion de confianza ─────────────────────────────────────────────
    high_conf   = sum(c >= 0.92 for c in val_confs)
    mid_conf    = sum(0.50 <= c < 0.92 for c in val_confs)
    low_conf    = sum(c < 0.50 for c in val_confs)
    total_val   = len(val_confs)

    print("\n" + "=" * 60)
    print("  DISTRIBUCION DE CONFIANZA (val) — umbrales del sistema")
    print("=" * 60)
    print(f"  >= 0.92 (auto-asigna) : {high_conf:>4} / {total_val}  ({high_conf/total_val*100:.1f}%)")
    print(f"  0.50-0.92 (sugiere)   : {mid_conf:>4} / {total_val}  ({mid_conf/total_val*100:.1f}%)")
    print(f"  < 0.50 (manual)       : {low_conf:>4} / {total_val}  ({low_conf/total_val*100:.1f}%)")

    # ── Ejemplos mal clasificados ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  EJEMPLOS MAL CLASIFICADOS (val, max 15)")
    print("=" * 60)
    errors = [
        (val_texts[i], val_targets[i], val_preds[i], val_confs[i])
        for i in range(len(val_preds))
        if val_preds[i] != val_targets[i]
    ]
    errors.sort(key=lambda x: x[3], reverse=True)  # los mas confiados-erroneos primero

    if not errors:
        print("  Sin errores en validacion. Verifica posible overfitting.")
    else:
        print(f"  Total errores: {len(errors)} / {total_val} ({len(errors)/total_val*100:.1f}%)")
        print(f"  {'Texto':<35} {'Real':<20} {'Predicho':<20} {'Conf':>5}")
        print("  " + "-" * 82)
        for text, real, pred, conf in errors[:15]:
            real_name = INDEX_TO_LABEL.get(real, str(real))
            pred_name = INDEX_TO_LABEL.get(pred, str(pred))
            print(f"  {text[:34]:<35} {real_name:<20} {pred_name:<20} {conf:>4.0%}")

    # ── Resumen final ─────────────────────────────────────────────────────────
    avg_f1 = sum(m["f1"] for m in val_metrics.values()) / num_classes
    print("\n" + "=" * 60)
    print("  RESUMEN FINAL")
    print("=" * 60)
    print(f"  Val accuracy media    : {val_acc*100:.1f}%")
    print(f"  F1 macro promedio     : {avg_f1*100:.1f}%")
    print(f"  Categorias con F1<70% : {low_f1_categories or 'ninguna'}")
    print(f"  Predicciones seguras  : {high_conf/total_val*100:.1f}% (>= 0.92)")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diagnostico del modelo DistilBERT")
    parser.add_argument("--model-path", default="/app/models", help="Directorio del modelo")
    args = parser.parse_args()
    main(args.model_path)
