"""Tests de importación CSV de transacciones (Fase 1.4)."""

from pathlib import Path

import pytest
from httpx import AsyncClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"

OPENBANK_CSV = (FIXTURES_DIR / "openbank_sample.csv").read_bytes()

# CSV con una fila de fecha inválida
MALFORMED_ROW_CSV = b"""Fecha;Concepto;Importe;Saldo
15/03/2026;SUPERMERCADO MERCADONA;-25,50;1500,50
FECHA_MALA;GASOLINERA BP;-45,00;1481,00
14/03/2026;NOMINA EMPRESA SA;2000,00;1526,00
"""

# CSV con una sola fila (para test de tipos de transacción)
INCOME_CSV = b"Fecha;Concepto;Importe;Saldo\n20/03/2026;NOMINA EMPRESA SA;2000,00;1526,00\n"
EXPENSE_CSV = b"Fecha;Concepto;Importe;Saldo\n20/03/2026;SUPERMERCADO MERCADONA;-25,50;1500,50\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_token(client: AsyncClient, email: str = "user@example.com") -> str:
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "securepass"}
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _create_account(client: AsyncClient, token: str, name: str = "Mi Cuenta") -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={"name": name, "bank": "OpenBank", "account_type": "checking", "currency": "EUR"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _import_url(account_id: str, dry_run: bool = False) -> str:
    params = f"?account_id={account_id}&dry_run={str(dry_run).lower()}"
    return f"/api/v1/transactions/import/csv{params}"


async def _do_import(
    client: AsyncClient,
    token: str,
    account_id: str,
    content: bytes = OPENBANK_CSV,
    dry_run: bool = False,
):
    return await client.post(
        _import_url(account_id, dry_run),
        files={"file": ("transactions.csv", content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_import_csv_success(client: AsyncClient):
    token = await _register_and_token(client)
    account_id = await _create_account(client, token)

    resp = await _do_import(client, token, account_id)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 3
    assert data["imported"] == 3
    assert data["skipped_duplicates"] == 0
    assert data["errors"] == 0
    assert data["dry_run"] is False
    assert len(data["rows"]) == 3
    # Todos los rows deben tener transaction_id asignado
    for row in data["rows"]:
        assert row["status"] == "imported"
        assert row["transaction_id"] is not None


async def test_import_csv_dry_run(client: AsyncClient):
    token = await _register_and_token(client)
    account_id = await _create_account(client, token)

    resp = await _do_import(client, token, account_id, dry_run=True)

    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 3
    assert data["dry_run"] is True
    # En dry_run no hay transaction_id
    for row in data["rows"]:
        assert row["transaction_id"] is None

    # Verificar que realmente no se crearon transacciones en BD
    list_resp = await client.get(
        f"/api/v1/transactions?account_id={account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.json()["total"] == 0


async def test_import_csv_deduplication(client: AsyncClient):
    token = await _register_and_token(client)
    account_id = await _create_account(client, token)

    # Primera importación
    resp1 = await _do_import(client, token, account_id)
    assert resp1.status_code == 200
    assert resp1.json()["imported"] == 3

    # Segunda importación del mismo CSV
    resp2 = await _do_import(client, token, account_id)
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["imported"] == 0
    assert data["skipped_duplicates"] == 3
    for row in data["rows"]:
        assert row["status"] == "skipped_duplicate"


async def test_import_csv_partial_duplicate(client: AsyncClient):
    token = await _register_and_token(client)
    account_id = await _create_account(client, token)

    # Importar solo la primera fila (MERCADONA)
    single_csv = b"Fecha;Concepto;Importe;Saldo\n15/03/2026;SUPERMERCADO MERCADONA;-25,50;1500,50\n"
    resp1 = await _do_import(client, token, account_id, content=single_csv)
    assert resp1.status_code == 200
    assert resp1.json()["imported"] == 1

    # Importar CSV completo: 1 duplicada + 2 nuevas
    resp2 = await _do_import(client, token, account_id)
    data = resp2.json()
    assert data["imported"] == 2
    assert data["skipped_duplicates"] == 1


async def test_import_csv_malformed_row(client: AsyncClient):
    token = await _register_and_token(client)
    account_id = await _create_account(client, token)

    resp = await _do_import(client, token, account_id, content=MALFORMED_ROW_CSV)
    assert resp.status_code == 200
    data = resp.json()
    assert data["errors"] == 1
    assert data["imported"] == 2
    assert data["total_rows"] == 3

    error_rows = [r for r in data["rows"] if r["status"] == "error"]
    assert len(error_rows) == 1
    assert error_rows[0]["error_detail"] is not None


async def test_import_csv_empty_file(client: AsyncClient):
    token = await _register_and_token(client)
    account_id = await _create_account(client, token)

    resp = await _do_import(client, token, account_id, content=b"")
    assert resp.status_code == 400


async def test_import_csv_wrong_account(client: AsyncClient):
    token = await _register_and_token(client)
    fake_account_id = "00000000-0000-0000-0000-000000000000"

    resp = await _do_import(client, token, fake_account_id)
    assert resp.status_code == 404


async def test_import_csv_other_users_account(client: AsyncClient):
    token_a = await _register_and_token(client, "a@example.com")
    token_b = await _register_and_token(client, "b@example.com")

    account_id_a = await _create_account(client, token_a)

    # Usuario B intenta importar en la cuenta de A
    resp = await _do_import(client, token_b, account_id_a)
    assert resp.status_code == 404


async def test_import_csv_no_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/transactions/import/csv?account_id=00000000-0000-0000-0000-000000000000",
        files={"file": ("transactions.csv", OPENBANK_CSV, "text/csv")},
    )
    assert resp.status_code == 401


async def test_import_csv_transaction_type_income(client: AsyncClient):
    token = await _register_and_token(client)
    account_id = await _create_account(client, token)

    resp = await _do_import(client, token, account_id, content=INCOME_CSV)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1

    # Verificar que el tipo es income
    list_resp = await client.get(
        f"/api/v1/transactions?account_id={account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    tx = list_resp.json()["items"][0]
    assert tx["transaction_type"] == "income"
    assert float(tx["amount"]) == 2000.00


async def test_import_csv_transaction_type_expense(client: AsyncClient):
    token = await _register_and_token(client)
    account_id = await _create_account(client, token)

    resp = await _do_import(client, token, account_id, content=EXPENSE_CSV)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1

    # Verificar que el tipo es expense
    list_resp = await client.get(
        f"/api/v1/transactions?account_id={account_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    tx = list_resp.json()["items"][0]
    assert tx["transaction_type"] == "expense"
    assert float(tx["amount"]) == -25.50
