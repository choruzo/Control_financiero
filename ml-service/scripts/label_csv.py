"""
Auto-categoriza un CSV de transacciones bancarias usando el modelo DistilBERT
y fusiona los resultados en real_dataset.json.

- Confianza >= THRESHOLD_AUTO  → se añade automáticamente al dataset
- Confianza <  THRESHOLD_AUTO  → se guarda en un archivo de revisión manual

Uso (dentro del contenedor ml-service):
    python scripts/label_csv.py --csv /app/data/movimientos.csv
    python scripts/label_csv.py --csv /app/data/movimientos.csv --threshold 0.90
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.ml.categories import INDEX_TO_LABEL

THRESHOLD_AUTO = 0.85   # confianza minima para auto-etiquetar


# ── Normalización (igual que preprocessor del ml-service) ────────────────────

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)

    # Eliminar sufijo OpenBank: ", CON LA TARJETA : xxxx EL yyyy-mm-dd"
    text = re.sub(
        r",?\s*CON\s+LA\s+TARJETA\s*:?\s*[\d\s]*EL\s+\d{4}-\d{2}-\d{2}",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Eliminar prefijos bancarios
    text = re.sub(
        r"^(?:COMPRA\s+EN\s+|COMPRA\s+TRJ\s+|COBRO\s+TPV\s+|REC\s+DOM\s+|"
        r"DOM\s+RECIBO\s+|TRANSFERENCIA\s+DE\s+|TRANSFERENCIA\s+A\s+FAVOR\s+DE\s+|"
        r"TRANSF\s+RECIB\s+DE\s+|ABONO\s+EN\s+CTA\s+|CARGO\s+EN\s+CTA\s+)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Eliminar número de tarjeta
    text = re.sub(r"\b\d{13,19}\b", "", text)

    # Eliminar fechas
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", text)
    text = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "", text)

    # Eliminar números largos
    text = re.sub(r"\b\d{6,}\b", "", text)

    # Limpiar caracteres especiales
    text = re.sub(r"[^\w\s\-áéíóúüñÁÉÍÓÚÜÑ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Inferencia en batch ───────────────────────────────────────────────────────

def predict_batch(
    texts: list[str],
    model,
    tokenizer,
    device: str,
    batch_size: int = 32,
) -> list[tuple[str, float]]:
    results = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        inputs = tokenizer(
            batch_texts,
            max_length=128,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        probs = F.softmax(outputs.logits, dim=-1)
        for prob_row in probs:
            idx = prob_row.argmax().item()
            conf = prob_row[idx].item()
            results.append((INDEX_TO_LABEL[idx], conf))
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main(csv_path: str, threshold: float, model_path: str, real_dataset_path: str) -> None:
    csv_file   = Path(csv_path)
    model_dir  = Path(model_path) / "categorizer"
    real_path  = Path(real_dataset_path)

    if not csv_file.exists():
        print(f"[ERROR] CSV no encontrado: {csv_file}")
        sys.exit(1)
    if not model_dir.exists():
        print(f"[ERROR] Modelo no encontrado en: {model_dir}")
        sys.exit(1)

    # Cargar modelo
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[OK] Cargando modelo desde {model_dir}  (device: {device})")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    model.to(device)
    model.eval()

    # Leer CSV
    print(f"[OK] Leyendo {csv_file.name}...")
    rows = []
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            concepto = row.get("Concepto", "").strip()
            if concepto:
                rows.append(concepto)

    print(f"     {len(rows)} transacciones encontradas")

    # Normalizar descripciones
    normalized = [normalize(r) for r in rows]

    # Filtrar vacias
    valid = [(orig, norm) for orig, norm in zip(rows, normalized) if len(norm) >= 3]
    print(f"     {len(valid)} con descripcion valida tras normalizar")

    # Predicción en batch
    print(f"[OK] Categorizando con threshold={threshold}...")
    orig_texts  = [v[0] for v in valid]
    norm_texts  = [v[1] for v in valid]
    predictions = predict_batch(norm_texts, model, tokenizer, device)

    # Separar por confianza
    auto_labeled   = []
    manual_review  = []

    for orig, norm, (label, conf) in zip(orig_texts, norm_texts, predictions):
        entry = {"text": norm, "label": label, "confidence": round(conf, 4), "original": orig}
        if conf >= threshold:
            auto_labeled.append(entry)
        else:
            manual_review.append(entry)

    # ── Fusionar con real_dataset.json ────────────────────────────────────────
    existing: list[dict] = []
    if real_path.exists():
        existing = json.loads(real_path.read_text(encoding="utf-8"))

    seen: set[str] = {item["text"].strip().upper() for item in existing}
    added = 0
    skipped_dup = 0

    for entry in auto_labeled:
        key = entry["text"].strip().upper()
        if key not in seen:
            seen.add(key)
            existing.append({"text": entry["text"], "label": entry["label"]})
            added += 1
        else:
            skipped_dup += 1

    # Guardar real_dataset.json actualizado
    real_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Guardar fichero de revisión manual
    review_path = Path(real_dataset_path).parent / "manual_review.json"
    review_path.write_text(
        json.dumps(manual_review, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ── Resumen ───────────────────────────────────────────────────────────────
    counts_auto   = Counter(e["label"] for e in auto_labeled)
    counts_manual = Counter(e["label"] for e in manual_review)

    print("\n" + "=" * 60)
    print("  RESULTADO CATEGORIZACION CSV")
    print("=" * 60)
    print(f"  Total transacciones     : {len(valid)}")
    print(f"  Auto-etiquetadas (>={threshold:.0%}): {len(auto_labeled)}")
    print(f"  Revision manual (<{threshold:.0%}) : {len(manual_review)}")
    print(f"  Nuevas anadidas al DS   : {added}")
    print(f"  Duplicados omitidos     : {skipped_dup}")
    print(f"  Total real_dataset.json : {len(existing)}")
    print("-" * 60)
    print("  Distribucion auto-etiquetadas:")
    for label in sorted(counts_auto):
        print(f"    {label:<25} {counts_auto[label]:>4}")
    if manual_review:
        print("-" * 60)
        print(f"  Ejemplos para revision manual ({len(manual_review)}):")
        for entry in manual_review[:20]:
            print(f"    [{entry['confidence']:.0%}] {entry['text'][:50]:<50} → {entry['label']}")
        if len(manual_review) > 20:
            print(f"    ... y {len(manual_review)-20} mas en {review_path}")
    print("=" * 60)
    print(f"\n[OK] real_dataset.json guardado: {real_path}")
    print(f"[OK] Revision manual guardada : {review_path}")
    print("\nSiguiente paso:")
    print("  python data/merge_datasets.py")
    print("  python scripts/train.py --epochs 20")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-categorizar CSV con DistilBERT")
    parser.add_argument("--csv",        required=True, help="Ruta al CSV de movimientos")
    parser.add_argument("--threshold",  type=float, default=THRESHOLD_AUTO, help="Confianza minima (default: 0.85)")
    parser.add_argument("--model-path", default="/app/models", help="Directorio del modelo")
    parser.add_argument("--dataset",    default="/app/data/real_dataset.json", help="real_dataset.json a actualizar")
    args = parser.parse_args()
    main(args.csv, args.threshold, args.model_path, args.dataset)
