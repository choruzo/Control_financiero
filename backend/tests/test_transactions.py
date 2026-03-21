from httpx import AsyncClient


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
