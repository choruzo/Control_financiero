"""
Fusiona real_dataset.json + synthetic_dataset.py en un único dataset.json.

Prioridad: los datos reales prevalecen sobre los sintéticos en caso de texto duplicado.

Uso:
    python data/merge_datasets.py

Salida:
    data/dataset.json
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# Añadimos el directorio raíz al path para poder importar synthetic_dataset
sys.path.insert(0, str(Path(__file__).parent))

from synthetic_dataset import DATASET as SYNTHETIC  # noqa: E402


def main() -> None:
    data_dir = Path(__file__).parent
    real_path = data_dir / "real_dataset.json"
    output_path = data_dir / "dataset.json"

    # ── Cargar datos reales ───────────────────────────────────────────────────
    real: list[dict[str, str]] = []
    if real_path.exists():
        real = json.loads(real_path.read_text(encoding="utf-8"))
        print(f"[OK] real_dataset.json cargado: {len(real)} entradas")
    else:
        print("[!] real_dataset.json no encontrado, se usara solo el sintetico")

    print(f"[OK] synthetic_dataset.py cargado: {len(SYNTHETIC)} entradas")

    # ── Merge con prioridad a datos reales ────────────────────────────────────
    # Los textos reales (normalizados) se guardan en un set para deduplicar
    seen: set[str] = set()
    merged: list[dict[str, str]] = []

    # 1. Primero los datos reales (máxima prioridad)
    for item in real:
        key = item["text"].strip().upper()
        if key not in seen:
            seen.add(key)
            merged.append(item)

    real_unique = len(merged)

    # 2. Luego los sintéticos (solo si el texto no existe ya)
    synthetic_added = 0
    synthetic_skipped = 0
    for item in SYNTHETIC:
        key = item["text"].strip().upper()
        if key not in seen:
            seen.add(key)
            merged.append(item)
            synthetic_added += 1
        else:
            synthetic_skipped += 1

    # ── Guardar ───────────────────────────────────────────────────────────────
    output_path.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ── Resumen ───────────────────────────────────────────────────────────────
    counts = Counter(item["label"] for item in merged)

    print("\n" + "=" * 55)
    print("  DATASET COMBINADO — RESUMEN")
    print("=" * 55)
    print(f"  Datos reales únicos   : {real_unique}")
    print(f"  Datos sintéticos añad.: {synthetic_added}")
    print(f"  Duplicados eliminados : {synthetic_skipped}")
    print(f"  TOTAL final           : {len(merged)}")
    print("─" * 55)
    print("  Distribución por categoría:")
    for label, count in sorted(counts.items()):
        bar = "#" * (count // 10)
        print(f"    {label:<25} {count:>4}  {bar}")
    print("=" * 55)
    print(f"\n[OK] Guardado en: {output_path}")


if __name__ == "__main__":
    main()
