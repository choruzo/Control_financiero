"""
Catálogo fijo de categorías del sistema para el modelo de categorización.

Las categorías deben coincidir con las sembradas por el seeder del backend
(services/categories.py). El índice numérico se usa internamente por el
clasificador DistilBERT; el backend resuelve el nombre a UUID via BD.
"""

CATEGORIES: list[dict] = [
    {"index": 0, "name": "Alimentación"},
    {"index": 1, "name": "Transporte"},
    {"index": 2, "name": "Ocio"},
    {"index": 3, "name": "Hogar"},
    {"index": 4, "name": "Salud"},
    {"index": 5, "name": "Educación"},
    {"index": 6, "name": "Ropa"},
    {"index": 7, "name": "Tecnología"},
    {"index": 8, "name": "Ingresos"},
    {"index": 9, "name": "Otros"},
]

LABEL_TO_INDEX: dict[str, int] = {c["name"]: c["index"] for c in CATEGORIES}
INDEX_TO_LABEL: dict[int, str] = {c["index"]: c["name"] for c in CATEGORIES}
NUM_LABELS: int = len(CATEGORIES)
CATEGORY_NAMES: list[str] = [c["name"] for c in CATEGORIES]
