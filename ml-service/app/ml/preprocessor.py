"""Normalización de texto bancario para mejorar la clasificación ML."""

import re
import unicodedata


def normalize_banking_text(text: str) -> str:
    """
    Normaliza un concepto bancario para reducir ruido antes de la inferencia.

    Operaciones aplicadas:
    - Normalizar caracteres Unicode (acentos, ñ, etc. se conservan)
    - Eliminar referencias numéricas largas (≥6 dígitos, como IDs de operación)
    - Eliminar fechas en formato DD/MM/YYYY o YYYY-MM-DD
    - Eliminar secuencias de caracteres no alfanuméricos (excepto espacios)
    - Normalizar espacios múltiples

    Nota: NO se convierte a minúsculas porque el modelo fue entrenado con texto en
    mayúsculas (formato estándar de extractos bancarios) y usa distilbert-base-multilingual-cased.
    """
    # Normalizar Unicode: separar letras de diacríticos combinados pero conservar ñ
    text = unicodedata.normalize("NFC", text)

    # Eliminar fechas (DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, etc.)
    text = re.sub(r"\b\d{1,4}[/-]\d{1,2}[/-]\d{2,4}\b", " ", text)

    # Eliminar referencias numéricas largas (≥6 dígitos seguidos)
    text = re.sub(r"\b\d{6,}\b", " ", text)

    # Reemplazar caracteres no alfanuméricos (salvo espacios) por espacio
    text = re.sub(r"[^\w\s]", " ", text)

    # Colapsar espacios múltiples
    text = re.sub(r"\s+", " ", text).strip()

    return text
