"""Normalización de texto bancario para mejorar la clasificación ML."""

import re
import unicodedata

# Prefijos operacionales que aparecen al inicio de conceptos bancarios españoles
# y no aportan información semántica sobre la categoría.
# Ejemplos reales: "REC DOM 20260201 IBERDROLA", "TRF 20260115 NOMINA EMPRESA"
_BANKING_PREFIXES = re.compile(
    r"^(?:"
    r"COMPRA\s+TRJ|"        # COMPRA TRJ 1234567890 MERCADONA → MERCADONA
    r"COBRO\s+TPV|"         # COBRO TPV 987654321 REPSOL → REPSOL
    r"REC\s+DOM|"           # REC DOM 20260201 IBERDROLA → IBERDROLA
    r"DOM\s+RECIBO|"        # DOM RECIBO 20250301 ENDESA → ENDESA
    r"TRF\s+|"              # TRF 20260115 NOMINA EMPRESA → NOMINA EMPRESA
    r"TRANSF\s+RECIB\s+DE|" # TRANSF RECIB DE JAVIER → JAVIER (transferencia recibida)
    r"TRANSF\s+EMIT|"       # TRANSF EMIT → transferencia emitida
    r"CTA\s+\w+\s+|"        # CTA 12345 NETFLIX → NETFLIX
    r"REINTEGRO\s+\d+\s+(?:EUR|€)?\s*|"  # REINTEGRO 300 EUR → vacío → Otros por contexto
    r"LIQUIDACION\s+|"      # LIQUIDACION TARJETA → TARJETA
    r"ABONO\s+EN\s+CTA|"    # ABONO EN CTA
    r"CARGO\s+EN\s+CTA|"    # CARGO EN CTA
    r"PAGO\s+CON\s+TRJ|"    # PAGO CON TRJ
    r"COMPRA\s+ON[\s-]?LINE\s+" # COMPRA ON LINE / COMPRA ONLINE
    r")\s*",
    re.IGNORECASE,
)


def normalize_banking_text(text: str) -> str:
    """
    Normaliza un concepto bancario para reducir ruido antes de la inferencia.

    Operaciones aplicadas:
    1. Normalizar caracteres Unicode (acentos, ñ, etc. se conservan)
    2. Eliminar prefijos operacionales bancarios (REC DOM, TRF, COBRO TPV, etc.)
    3. Eliminar fechas en formato DD/MM/YYYY o YYYY-MM-DD
    4. Eliminar referencias numéricas largas (≥6 dígitos, como IDs de operación)
    5. Eliminar caracteres no alfanuméricos (excepto espacios)
    6. Normalizar espacios múltiples

    Nota: NO se convierte a minúsculas porque el modelo fue entrenado con texto en
    mayúsculas (formato estándar de extractos bancarios) y usa distilbert-base-multilingual-cased.
    """
    # 1. Normalizar Unicode
    text = unicodedata.normalize("NFC", text)

    # 2. Eliminar prefijos operacionales bancarios al inicio del concepto
    text = _BANKING_PREFIXES.sub("", text)

    # 3. Eliminar fechas compactas sin separador (YYYYMMDD, ej: 20260115)
    text = re.sub(r"\b20\d{6}\b", " ", text)

    # 4. Eliminar fechas con separador (DD/MM/YYYY, YYYY-MM-DD, etc.)
    text = re.sub(r"\b\d{1,4}[/-]\d{1,2}[/-]\d{2,4}\b", " ", text)

    # 5. Eliminar referencias numéricas largas (≥6 dígitos seguidos)
    text = re.sub(r"\b\d{6,}\b", " ", text)

    # 6. Reemplazar caracteres no alfanuméricos (salvo espacios) por espacio
    text = re.sub(r"[^\w\s]", " ", text)

    # 7. Colapsar espacios múltiples
    text = re.sub(r"\s+", " ", text).strip()

    return text
