"""Parser CSV para importación de transacciones bancarias.

Soporta el formato de exportación de OpenBank (banco digital español).
"""

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


@dataclass
class ParsedRow:
    """Fila CSV parseada correctamente."""

    row_index: int  # 1-based, sin contar la cabecera
    date: date
    description: str
    amount: Decimal  # signed: negativo=gasto, positivo=ingreso
    raw_line: str


@dataclass
class RowParseError:
    """Error al parsear una fila CSV."""

    row_index: int  # 1-based, sin contar la cabecera
    raw_line: str
    error: str


def _decode_content(content: bytes) -> str:
    """Intenta decodificar bytes como UTF-8, luego como latin-1."""
    try:
        return content.decode("utf-8-sig")  # utf-8-sig elimina BOM si existe
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _parse_openbank_date(value: str) -> date:
    """Parsea fecha en formato DD/MM/YYYY."""
    parts = value.strip().split("/")
    if len(parts) != 3:
        raise ValueError(f"Formato de fecha inválido: '{value}' (esperado DD/MM/YYYY)")
    day, month, year = parts
    return date(int(year), int(month), int(day))


def _parse_openbank_amount(value: str) -> Decimal:
    """Parsea importe en formato OpenBank (coma decimal, punto de miles opcional)."""
    # Quitar espacios y posibles símbolos de moneda
    cleaned = value.strip().replace(" ", "").replace("€", "")
    # Quitar puntos de miles (1.234,56 → 1234,56)
    cleaned = cleaned.replace(".", "")
    # Reemplazar coma decimal por punto
    cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation as e:
        raise ValueError(f"Importe inválido: '{value}'") from e


def parse_openbank_csv(
    content: bytes,
) -> tuple[list[ParsedRow], list[RowParseError]]:
    """Parsea un CSV en formato OpenBank.

    Formato esperado:
        Fecha;Concepto;Importe;Saldo
        21/03/2026;SUPERMERCADO MERCADONA;-25,50;1500,50

    Args:
        content: Bytes del archivo CSV.

    Returns:
        Tupla (filas_válidas, errores). Las filas con error van a la lista de errores.
    """
    text = _decode_content(content)
    reader = csv.reader(io.StringIO(text), delimiter=";")

    parsed: list[ParsedRow] = []
    errors: list[RowParseError] = []

    row_index = 0  # filas de datos (sin cabecera)
    for _i, row in enumerate(reader):
        # Saltar filas vacías
        if not any(cell.strip() for cell in row):
            continue

        # La primera fila no vacía es la cabecera — saltarla
        if row_index == 0:
            row_index += 1
            continue

        raw_line = ";".join(row)

        if len(row) < 3:
            errors.append(
                RowParseError(
                    row_index=row_index,
                    raw_line=raw_line,
                    error=f"Número de columnas insuficiente (encontradas {len(row)}, mínimo 3)",
                )
            )
            row_index += 1
            continue

        try:
            parsed_date = _parse_openbank_date(row[0])
        except (ValueError, IndexError) as e:
            errors.append(RowParseError(row_index=row_index, raw_line=raw_line, error=str(e)))
            row_index += 1
            continue

        try:
            amount = _parse_openbank_amount(row[2])
        except ValueError as e:
            errors.append(RowParseError(row_index=row_index, raw_line=raw_line, error=str(e)))
            row_index += 1
            continue

        description = row[1].strip()[:255]  # Concepto, truncado a 255 chars

        parsed.append(
            ParsedRow(
                row_index=row_index,
                date=parsed_date,
                description=description,
                amount=amount,
                raw_line=raw_line,
            )
        )
        row_index += 1

    return parsed, errors
