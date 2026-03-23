"""
Exporta transacciones reales de la BD como dataset de entrenamiento ML.

Uso (desde el contenedor backend):
    python scripts/export_training_data.py --output /tmp/real_dataset.json

El script:
1. Conecta a PostgreSQL via DATABASE_URL
2. Obtiene todas las transacciones con categoría asignada
3. Mapea las categorías de la BD a las categorías del modelo ML
4. Exporta como data/dataset.json compatible con ml-service/scripts/train.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Mapping: nombre de categoría en BD → categoría ML
CATEGORY_MAP: dict[str, str] = {
    # Alimentación
    "Alimentación": "Alimentación",
    "Cafeterías": "Alimentación",
    "Restaurantes": "Alimentación",
    "Supermercado": "Alimentación",
    # Transporte
    "Transporte": "Transporte",
    "Transporte público": "Transporte",
    "Taxi/Uber": "Transporte",
    "Gasolina": "Transporte",
    # Ocio
    "Ocio": "Ocio",
    "Entretenimiento": "Ocio",
    "Deporte": "Ocio",
    "Viajes": "Ocio",
    # Hogar
    "Hogar": "Hogar",
    "Suministros": "Hogar",
    "Alquiler/Hipoteca": "Hogar",
    "Mantenimiento": "Hogar",
    # Salud
    "Salud": "Salud",
    "Médico": "Salud",
    "Farmacia": "Salud",
    "Seguro médico": "Salud",
    # Educación
    "Educación": "Educación",
    "Libros": "Educación",
    "Cursos": "Educación",
    # Ropa y calzado
    "Ropa y calzado": "Ropa y calzado",
    # Tecnología
    "Tecnología": "Tecnología",
    # Ingresos
    "Ingresos": "Ingresos",
    "Nómina": "Ingresos",
    "Intereses/Dividendos": "Ingresos",
    "Freelance": "Ingresos",
    # Otros
    "Otros": "Otros",
    "Seguros": "Otros",
}

# Categorías a excluir (demasiado ruidosas o incorrectamente asignadas)
EXCLUDE_CATEGORIES = set()

# Descripciones específicas a excluir (claramente mal etiquetadas)
EXCLUDE_DESCRIPTIONS_SUBSTR = [
    "L0GF42 INDRA BITES",  # Restaurante empresa etiquetado como Nómina
]


def normalize_banking_text(text: str) -> str:
    """Replica la normalización del ml-service para consistencia."""
    import re
    import unicodedata

    text = unicodedata.normalize("NFC", text)

    # Eliminar sufijo OpenBank: ",CON LA TARJETA : 1234... EL"
    text = re.sub(
        r",?\s*CON\s+LA\s+TARJETA\s*:?\s*[\d\s]*EL\s*",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Eliminar prefijos operacionales
    prefixes = re.compile(
        r"^(?:"
        r"Samsung\s+pay:\s*|"
        r"COMPRA\s+TRJ\s*|"
        r"COBRO\s+TPV\s*|"
        r"REC\s+DOM\s*|"
        r"DOM\s+RECIBO\s*|"
        r"TRF\s+|"
        r"TRANSF\s+RECIB\s+DE\s+|"
        r"TRANSF\s+EMIT\s*|"
        r"CTA\s+\w+\s+|"
        r"REINTEGRO\s+\d+\s+(?:EUR|€)?\s*|"
        r"LIQUIDACION\s+INTERESES\s+DEL\s+CONTRATO\s*|"
        r"ABONO\s+EN\s+CTA\s*|"
        r"CARGO\s+EN\s+CTA\s*|"
        r"PAGO\s+CON\s+TRJ\s*|"
        r"COMPRA\s+ON[\s-]?LINE\s+|"
        r"COMPRA\s+EN\s+"
        r")\s*",
        re.IGNORECASE,
    )
    text = prefixes.sub("", text)

    # Eliminar fechas
    text = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", "", text)
    text = re.sub(r"\b\d{4}[-/]\d{2}[-/]\d{2}\b", "", text)

    # Eliminar números largos (>5 dígitos)
    text = re.sub(r"\b\d{6,}\b", "", text)

    # Limpiar caracteres no alfanuméricos (conservar espacios y guiones)
    text = re.sub(r"[^\w\s\-áéíóúüñÁÉÍÓÚÜÑ]", " ", text)

    # Normalizar espacios
    text = re.sub(r"\s+", " ", text).strip()

    return text


def main(output_path: str) -> None:
    import os

    import asyncio
    import asyncpg

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        db_url = (
            f"postgresql://{os.environ.get('POSTGRES_USER', 'fincontrol')}"
            f":{os.environ.get('POSTGRES_PASSWORD', 'fincontrol')}"
            f"@{os.environ.get('POSTGRES_HOST', 'postgres')}"
            f":5432/{os.environ.get('POSTGRES_DB', 'fincontrol')}"
        )

    # asyncpg usa postgresql:// (sin +asyncpg)
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    async def fetch_rows() -> list:
        conn = await asyncpg.connect(db_url)
        try:
            return await conn.fetch(
                """
                SELECT t.description, c.name
                FROM transactions t
                JOIN categories c ON t.category_id = c.id
                WHERE t.description IS NOT NULL AND t.description != ''
                ORDER BY c.name, t.description
                """
            )
        finally:
            await conn.close()

    rows = asyncio.run(fetch_rows())

    examples = []
    skipped = 0
    for description, category_name in rows:
        # Excluir categorías no mapeadas
        if category_name not in CATEGORY_MAP:
            skipped += 1
            continue

        # Excluir descripciones problemáticas
        if any(excl in description for excl in EXCLUDE_DESCRIPTIONS_SUBSTR):
            skipped += 1
            continue

        ml_label = CATEGORY_MAP[category_name]
        normalized = normalize_banking_text(description)

        if not normalized or len(normalized) < 3:
            skipped += 1
            continue

        examples.append({"text": normalized, "label": ml_label})

    Path(output_path).write_text(json.dumps(examples, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    counts = Counter(e["label"] for e in examples)
    print(f"Exportados: {len(examples)} ejemplos (saltados: {skipped})")
    print(f"Distribución: {dict(sorted(counts.items()))}")
    print(f"Guardado en: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/real_dataset.json")
    args = parser.parse_args()
    main(args.output)
