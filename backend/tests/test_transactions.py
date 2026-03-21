import respx
from httpx import AsyncClient, Response

ML_BASE = "http://ml-service:8001"


def _ml_auto_assign_payload(category_name: str = "Alimentación", category_id: int = 0) -> dict:
    return {
        "category_id": category_id,
        "category_name": category_name,
        "confidence": 0.95,
        "auto_assigned": True,
        "suggested": False,
        "model_version": "1.0",
    }


def _ml_suggest_payload(category_name: str = "Transporte", category_id: int = 1) -> dict:
    return {
        "category_id": category_id,
        "category_name": category_name,
        "confidence": 0.65,
        "auto_assigned": False,
        "suggested": True,
        "model_version": "1.0",
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_and_token(client: AsyncClient, email: str = "tx@example.com") -> str:
    reg = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "securepass"}
    )
    return reg.json()["access_token"]


async def _create_account(client: AsyncClient, token: str, name: str = "Cuenta") -> dict:
    resp = await client.post(
        "/api/v1/accounts",
        json={"name": name, "bank": "Banco", "account_type": "checking"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


async def _create_tx(client: AsyncClient, token: str, account_id: str, **overrides) -> dict:
    payload = {
        "account_id": account_id,
        "amount": "-20.00",
        "description": "Compra",
        "transaction_type": "expense",
        "date": "2026-03-15",
        **overrides,
    }
    return await client.post(
        "/api/v1/transactions",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )


# ── POST /transactions ────────────────────────────────────────────────────────

async def test_create_transaction_expense(client: AsyncClient):
    token = await _register_and_token(client)
    account = await _create_account(client, token)
    resp = await _create_tx(client, token, account["id"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["transaction_type"] == "expense"
    assert data["amount"] == "-20.00"


async def test_create_transaction_income(client: AsyncClient):
    token = await _register_and_token(client, "income@example.com")
    account = await _create_account(client, token)
    resp = await _create_tx(
        client, token, account["id"],
        amount="2500.00", description="Nómina", transaction_type="income"
    )
    assert resp.status_code == 201
    assert resp.json()["transaction_type"] == "income"


async def test_create_transaction_wrong_account(client: AsyncClient):
    token = await _register_and_token(client, "wrong_acc@example.com")
    resp = await _create_tx(client, token, "00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_create_transaction_no_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/transactions",
        json={"account_id": "00000000-0000-0000-0000-000000000000",
              "amount": "10", "description": "X",
              "transaction_type": "expense", "date": "2026-01-01"},
    )
    assert resp.status_code == 401


async def test_create_transaction_other_users_account(client: AsyncClient):
    """User B cannot create a transaction on user A's account."""
    token_a = await _register_and_token(client, "acc_a@example.com")
    token_b = await _register_and_token(client, "acc_b@example.com")
    account_a = await _create_account(client, token_a)
    resp = await _create_tx(client, token_b, account_a["id"])
    assert resp.status_code == 404


# ── GET /transactions ─────────────────────────────────────────────────────────

async def test_list_transactions_empty(client: AsyncClient):
    token = await _register_and_token(client, "empty_tx@example.com")
    resp = await client.get(
        "/api/v1/transactions", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_transactions_pagination(client: AsyncClient):
    token = await _register_and_token(client, "page@example.com")
    account = await _create_account(client, token)
    for i in range(5):
        await _create_tx(client, token, account["id"], description=f"TX {i}")

    resp = await client.get(
        "/api/v1/transactions?page=1&per_page=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 3
    assert data["pages"] == 2
    assert data["page"] == 1

    resp2 = await client.get(
        "/api/v1/transactions?page=2&per_page=3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.json()["page"] == 2
    assert len(resp2.json()["items"]) == 2


async def test_filter_by_date_range(client: AsyncClient):
    token = await _register_and_token(client, "date_filter@example.com")
    account = await _create_account(client, token)
    await _create_tx(client, token, account["id"], date="2026-01-10")
    await _create_tx(client, token, account["id"], date="2026-02-15")
    await _create_tx(client, token, account["id"], date="2026-03-20")

    resp = await client.get(
        "/api/v1/transactions?date_from=2026-02-01&date_to=2026-02-28",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["date"] == "2026-02-15"


async def test_filter_by_type(client: AsyncClient):
    token = await _register_and_token(client, "type_filter@example.com")
    account = await _create_account(client, token)
    await _create_tx(client, token, account["id"], transaction_type="expense")
    await _create_tx(client, token, account["id"], transaction_type="income", amount="100.00")

    resp = await client.get(
        "/api/v1/transactions?transaction_type=income",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["transaction_type"] == "income"


async def test_filter_by_account(client: AsyncClient):
    token = await _register_and_token(client, "acc_filter@example.com")
    acc1 = await _create_account(client, token, name="Acc1")
    acc2 = await _create_account(client, token, name="Acc2")
    await _create_tx(client, token, acc1["id"])
    await _create_tx(client, token, acc1["id"])
    await _create_tx(client, token, acc2["id"])

    resp = await client.get(
        f"/api/v1/transactions?account_id={acc1['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["total"] == 2


async def test_filter_by_amount_range(client: AsyncClient):
    token = await _register_and_token(client, "amount_filter@example.com")
    account = await _create_account(client, token)
    await _create_tx(client, token, account["id"], amount="-10.00")
    await _create_tx(client, token, account["id"], amount="-50.00")
    await _create_tx(client, token, account["id"], amount="-200.00")

    resp = await client.get(
        "/api/v1/transactions?min_amount=-100&max_amount=-1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.json()["total"] == 2


# ── GET /transactions/{id} ────────────────────────────────────────────────────

async def test_get_transaction(client: AsyncClient):
    token = await _register_and_token(client, "get_tx@example.com")
    account = await _create_account(client, token)
    tx = (await _create_tx(client, token, account["id"])).json()
    resp = await client.get(
        f"/api/v1/transactions/{tx['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == tx["id"]


async def test_get_transaction_other_user(client: AsyncClient):
    token_a = await _register_and_token(client, "gtx_a@example.com")
    token_b = await _register_and_token(client, "gtx_b@example.com")
    account = await _create_account(client, token_a)
    tx = (await _create_tx(client, token_a, account["id"])).json()
    resp = await client.get(
        f"/api/v1/transactions/{tx['id']}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp.status_code == 404


# ── PATCH /transactions/{id} ──────────────────────────────────────────────────

async def test_update_transaction(client: AsyncClient):
    token = await _register_and_token(client, "upd_tx@example.com")
    account = await _create_account(client, token)
    tx = (await _create_tx(client, token, account["id"])).json()
    resp = await client.patch(
        f"/api/v1/transactions/{tx['id']}",
        json={"description": "Actualizado", "amount": "-35.00"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Actualizado"
    assert resp.json()["amount"] == "-35.00"


# ── DELETE /transactions/{id} ─────────────────────────────────────────────────

async def test_delete_transaction(client: AsyncClient):
    token = await _register_and_token(client, "del_tx@example.com")
    account = await _create_account(client, token)
    tx = (await _create_tx(client, token, account["id"])).json()
    resp = await client.delete(
        f"/api/v1/transactions/{tx['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 204
    get_resp = await client.get(
        f"/api/v1/transactions/{tx['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert get_resp.status_code == 404


# ── Integración ML en POST /transactions ──────────────────────────────────────


async def test_create_transaction_ml_fields_present_in_response(client: AsyncClient):
    """La respuesta de POST /transactions incluye los campos ML (None cuando ML no disponible)."""
    token = await _register_and_token(client, "ml_fields@example.com")
    account = await _create_account(client, token)
    resp = await _create_tx(client, token, account["id"])
    assert resp.status_code == 201
    data = resp.json()
    assert "ml_suggested_category_id" in data
    assert "ml_confidence" in data


async def test_create_transaction_ml_unavailable_does_not_fail(client: AsyncClient):
    """Cuando el ML service no está disponible, la transacción se crea igualmente sin categoría."""
    token = await _register_and_token(client, "ml_unavail@example.com")
    account = await _create_account(client, token)
    resp = await _create_tx(client, token, account["id"], description="MERCADONA SA COMPRA")
    assert resp.status_code == 201
    data = resp.json()
    # ML no disponible en tests → sin categoría ni sugerencia
    assert data["ml_suggested_category_id"] is None
    assert data["ml_confidence"] is None


@respx.mock
async def test_create_transaction_ml_auto_assigns_category(client: AsyncClient):
    """Cuando ML devuelve auto_assigned=True, la transacción queda con category_id asignado."""
    respx.post(f"{ML_BASE}/predict").mock(
        return_value=Response(200, json=_ml_auto_assign_payload("Alimentación", 0))
    )
    token = await _register_and_token(client, "ml_auto@example.com")
    account = await _create_account(client, token)
    resp = await _create_tx(client, token, account["id"], description="MERCADONA SA COMPRA")
    assert resp.status_code == 201
    data = resp.json()
    # Con auto_assigned=True la categoría queda asignada
    assert data["category_id"] is not None
    # No hay sugerencia pendiente (ya asignada)
    assert data["ml_suggested_category_id"] is None


@respx.mock
async def test_create_transaction_ml_suggests_category(client: AsyncClient):
    """Cuando ML devuelve suggested=True, ml_suggested_category_id se puebla en la respuesta."""
    respx.post(f"{ML_BASE}/predict").mock(
        return_value=Response(200, json=_ml_suggest_payload("Transporte", 1))
    )
    token = await _register_and_token(client, "ml_suggest@example.com")
    account = await _create_account(client, token)
    resp = await _create_tx(client, token, account["id"], description="REPSOL GASOLINERA")
    assert resp.status_code == 201
    data = resp.json()
    # Con suggested=True: no asigna categoría pero devuelve sugerencia
    assert data["category_id"] is None
    assert data["ml_suggested_category_id"] is not None
    assert data["ml_confidence"] == 0.65


@respx.mock
async def test_create_transaction_with_explicit_category_skips_ml(client: AsyncClient):
    """Si el usuario ya indica category_id, no se llama al ML service."""
    # El mock NO debe ser invocado
    mock_route = respx.post(f"{ML_BASE}/predict").mock(
        return_value=Response(200, json=_ml_auto_assign_payload())
    )
    token = await _register_and_token(client, "ml_skip@example.com")
    account = await _create_account(client, token)

    # Obtener una categoría del sistema
    cats = await client.get(
        "/api/v1/categories", headers={"Authorization": f"Bearer {token}"}
    )
    category_id = cats.json()[0]["id"]

    resp = await _create_tx(client, token, account["id"], category_id=category_id)
    assert resp.status_code == 201
    # El mock no debe haberse llamado
    assert not mock_route.called
