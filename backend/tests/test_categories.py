import pytest
from httpx import AsyncClient

from app.services.categories import seed_default_categories


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_and_token(client: AsyncClient, email: str = "cat@example.com") -> str:
    reg = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "securepass"}
    )
    return reg.json()["access_token"]


async def _create_category(client: AsyncClient, token: str, **overrides) -> dict:
    payload = {"name": "Mi Categoría", **overrides}
    return await client.post(
        "/api/v1/categories", json=payload, headers={"Authorization": f"Bearer {token}"}
    )


# ── POST /categories ───────────────────────────────────────────────────────────

async def test_create_category(client: AsyncClient):
    token = await _register_and_token(client)
    resp = await _create_category(client, token)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Mi Categoría"
    assert data["is_system"] is False
    assert data["parent_id"] is None


async def test_create_subcategory(client: AsyncClient):
    token = await _register_and_token(client, "sub@example.com")
    parent = (await _create_category(client, token, name="Padre")).json()
    resp = await _create_category(client, token, name="Hijo", parent_id=parent["id"])
    assert resp.status_code == 201
    assert resp.json()["parent_id"] == parent["id"]


async def test_create_category_no_auth(client: AsyncClient):
    resp = await client.post("/api/v1/categories", json={"name": "X"})
    assert resp.status_code == 401


# ── GET /categories ────────────────────────────────────────────────────────────

async def test_list_categories_includes_system(client: AsyncClient):
    token = await _register_and_token(client, "list@example.com")
    # System categories are seeded at startup (lifespan), but the test client
    # bypasses lifespan. Seed manually.
    from app.database import get_db
    from app.main import app

    # Access the overridden session from the app's dependency_overrides
    db_gen = app.dependency_overrides[get_db]()
    db = await db_gen.__anext__()
    try:
        await seed_default_categories(db)
        await db.commit()
    finally:
        await db_gen.aclose()

    resp = await client.get("/api/v1/categories", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    categories = resp.json()
    system_cats = [c for c in categories if c["is_system"]]
    assert len(system_cats) > 0


async def test_list_categories_user_sees_own(client: AsyncClient):
    token_a = await _register_and_token(client, "own_a@example.com")
    token_b = await _register_and_token(client, "own_b@example.com")
    await _create_category(client, token_a, name="Solo de A")

    resp_b = await client.get(
        "/api/v1/categories", headers={"Authorization": f"Bearer {token_b}"}
    )
    names = [c["name"] for c in resp_b.json()]
    assert "Solo de A" not in names


# ── GET /categories/{id} ───────────────────────────────────────────────────────

async def test_get_category(client: AsyncClient):
    token = await _register_and_token(client, "get_cat@example.com")
    cat = (await _create_category(client, token)).json()
    resp = await client.get(
        f"/api/v1/categories/{cat['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == cat["id"]


# ── PATCH /categories/{id} ────────────────────────────────────────────────────

async def test_update_category(client: AsyncClient):
    token = await _register_and_token(client, "upd_cat@example.com")
    cat = (await _create_category(client, token)).json()
    resp = await client.patch(
        f"/api/v1/categories/{cat['id']}",
        json={"name": "Renombrada", "color": "#FF0000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renombrada"
    assert resp.json()["color"] == "#FF0000"


async def test_cannot_update_system_category(client: AsyncClient):
    token = await _register_and_token(client, "sys_upd@example.com")
    from app.database import get_db
    from app.main import app
    from sqlalchemy import select
    from app.models.category import Category

    db_gen = app.dependency_overrides[get_db]()
    db = await db_gen.__anext__()
    try:
        await seed_default_categories(db)
        await db.commit()
        result = await db.execute(select(Category).where(Category.is_system.is_(True)).limit(1))
        sys_cat = result.scalar_one()
        sys_cat_id = str(sys_cat.id)
    finally:
        await db_gen.aclose()

    resp = await client.patch(
        f"/api/v1/categories/{sys_cat_id}",
        json={"name": "Hacked"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── DELETE /categories/{id} ───────────────────────────────────────────────────

async def test_delete_category(client: AsyncClient):
    token = await _register_and_token(client, "del_cat@example.com")
    cat = (await _create_category(client, token)).json()
    resp = await client.delete(
        f"/api/v1/categories/{cat['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 204
    get_resp = await client.get(
        f"/api/v1/categories/{cat['id']}", headers={"Authorization": f"Bearer {token}"}
    )
    assert get_resp.status_code == 404


async def test_cannot_delete_system_category(client: AsyncClient):
    token = await _register_and_token(client, "sys_del@example.com")
    from app.database import get_db
    from app.main import app
    from sqlalchemy import select
    from app.models.category import Category

    db_gen = app.dependency_overrides[get_db]()
    db = await db_gen.__anext__()
    try:
        await seed_default_categories(db)
        await db.commit()
        result = await db.execute(select(Category).where(Category.is_system.is_(True)).limit(1))
        sys_cat = result.scalar_one()
        sys_cat_id = str(sys_cat.id)
    finally:
        await db_gen.aclose()

    resp = await client.delete(
        f"/api/v1/categories/{sys_cat_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── Seeder ────────────────────────────────────────────────────────────────────

async def test_seed_categories_idempotent(client: AsyncClient):
    """Running seed twice must not duplicate categories."""
    from app.database import get_db
    from app.main import app
    from sqlalchemy import func, select
    from app.models.category import Category

    db_gen = app.dependency_overrides[get_db]()
    db = await db_gen.__anext__()
    try:
        await seed_default_categories(db)
        await seed_default_categories(db)  # second call
        await db.commit()
        result = await db.execute(
            select(func.count()).select_from(Category).where(Category.is_system.is_(True))
        )
        count = result.scalar_one()
    finally:
        await db_gen.aclose()

    # Should have inserted only once
    assert count > 0
    # Re-seeding should not double
    db_gen2 = app.dependency_overrides[get_db]()
    db2 = await db_gen2.__anext__()
    try:
        await seed_default_categories(db2)
        await db2.commit()
        result2 = await db2.execute(
            select(func.count()).select_from(Category).where(Category.is_system.is_(True))
        )
        count2 = result2.scalar_one()
    finally:
        await db_gen2.aclose()

    assert count == count2
