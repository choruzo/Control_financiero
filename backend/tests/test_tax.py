"""Integration tests for the fiscalidad module (Fase 2.5)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_and_token(client: AsyncClient, email: str = "tax@test.com") -> str:
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Secret123!"}
    )
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_config(
    client: AsyncClient, token: str, year: int = 2025, gross: float = 30000.0
) -> dict:
    resp = await client.post(
        "/api/v1/tax/configs",
        json={"tax_year": year, "gross_annual_salary": gross},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()


# ── GET /tax/brackets ─────────────────────────────────────────────────────────


async def test_list_brackets_2025(client: AsyncClient):
    """After startup the seeder must have inserted 2025 brackets."""
    token = await _register_and_token(client)
    resp = await client.get("/api/v1/tax/brackets?year=2025", headers=_auth(token))

    assert resp.status_code == 200
    data = resp.json()
    # 6 general + 5 savings = 11
    assert len(data) == 11


async def test_list_brackets_2026(client: AsyncClient):
    token = await _register_and_token(client, email="tax2026@test.com")
    resp = await client.get("/api/v1/tax/brackets?year=2026", headers=_auth(token))

    assert resp.status_code == 200
    assert len(resp.json()) == 11


async def test_list_brackets_filtered_by_type(client: AsyncClient):
    token = await _register_and_token(client, email="taxtype@test.com")
    resp = await client.get(
        "/api/v1/tax/brackets?year=2025&bracket_type=general", headers=_auth(token)
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 6
    assert all(b["bracket_type"] == "general" for b in data)


async def test_list_brackets_savings_type(client: AsyncClient):
    token = await _register_and_token(client, email="taxsav@test.com")
    resp = await client.get(
        "/api/v1/tax/brackets?year=2025&bracket_type=savings", headers=_auth(token)
    )

    assert resp.status_code == 200
    assert len(resp.json()) == 5


async def test_brackets_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/tax/brackets")
    assert resp.status_code == 401


# ── POST /tax/configs ─────────────────────────────────────────────────────────


async def test_create_tax_config_success(client: AsyncClient):
    token = await _register_and_token(client, email="taxcreate@test.com")
    resp = await client.post(
        "/api/v1/tax/configs",
        json={"tax_year": 2025, "gross_annual_salary": 35000},
        headers=_auth(token),
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["tax_year"] == 2025
    assert float(data["gross_annual_salary"]) == pytest.approx(35000, abs=0.01)
    assert "id" in data


async def test_create_tax_config_duplicate_year_fails(client: AsyncClient):
    token = await _register_and_token(client, email="taxdup@test.com")
    await _create_config(client, token, year=2025)

    resp = await client.post(
        "/api/v1/tax/configs",
        json={"tax_year": 2025, "gross_annual_salary": 40000},
        headers=_auth(token),
    )
    assert resp.status_code == 409


async def test_create_tax_config_year_out_of_range_fails(client: AsyncClient):
    token = await _register_and_token(client, email="taxrange@test.com")
    resp = await client.post(
        "/api/v1/tax/configs",
        json={"tax_year": 1990, "gross_annual_salary": 30000},
        headers=_auth(token),
    )
    assert resp.status_code == 422


async def test_create_tax_config_zero_salary_fails(client: AsyncClient):
    token = await _register_and_token(client, email="taxzero@test.com")
    resp = await client.post(
        "/api/v1/tax/configs",
        json={"tax_year": 2025, "gross_annual_salary": 0},
        headers=_auth(token),
    )
    assert resp.status_code == 422


async def test_configs_require_auth(client: AsyncClient):
    resp = await client.get("/api/v1/tax/configs")
    assert resp.status_code == 401


# ── GET /tax/configs ──────────────────────────────────────────────────────────


async def test_list_tax_configs_empty(client: AsyncClient):
    token = await _register_and_token(client, email="taxempty@test.com")
    resp = await client.get("/api/v1/tax/configs", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_tax_configs_user_isolation(client: AsyncClient):
    token_a = await _register_and_token(client, email="taxiso_a@test.com")
    token_b = await _register_and_token(client, email="taxiso_b@test.com")

    await _create_config(client, token_a, year=2025)

    resp = await client.get("/api/v1/tax/configs", headers=_auth(token_b))
    assert resp.json() == []


async def test_list_tax_configs_multiple_years(client: AsyncClient):
    token = await _register_and_token(client, email="taxmulti@test.com")
    await _create_config(client, token, year=2025)
    await _create_config(client, token, year=2026, gross=32000)

    resp = await client.get("/api/v1/tax/configs", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── GET /tax/configs/{id} ─────────────────────────────────────────────────────


async def test_get_tax_config_success(client: AsyncClient):
    token = await _register_and_token(client, email="taxget@test.com")
    created = await _create_config(client, token, year=2025)
    config_id = created["id"]

    resp = await client.get(f"/api/v1/tax/configs/{config_id}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == config_id


async def test_get_tax_config_not_found(client: AsyncClient):
    token = await _register_and_token(client, email="taxnf@test.com")
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = await client.get(f"/api/v1/tax/configs/{fake_id}", headers=_auth(token))
    assert resp.status_code == 404


# ── PATCH /tax/configs/{id} ───────────────────────────────────────────────────


async def test_update_tax_config(client: AsyncClient):
    token = await _register_and_token(client, email="taxupd@test.com")
    cfg = await _create_config(client, token, year=2025, gross=30000)

    resp = await client.patch(
        f"/api/v1/tax/configs/{cfg['id']}",
        json={"gross_annual_salary": 40000},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    assert float(resp.json()["gross_annual_salary"]) == pytest.approx(40000, abs=0.01)


# ── DELETE /tax/configs/{id} ──────────────────────────────────────────────────


async def test_delete_tax_config(client: AsyncClient):
    token = await _register_and_token(client, email="taxdel@test.com")
    cfg = await _create_config(client, token, year=2025)

    del_resp = await client.delete(
        f"/api/v1/tax/configs/{cfg['id']}", headers=_auth(token)
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/tax/configs/{cfg['id']}", headers=_auth(token)
    )
    assert get_resp.status_code == 404


# ── GET /tax/configs/{id}/calculation ────────────────────────────────────────


async def test_calculation_fields_present(client: AsyncClient):
    token = await _register_and_token(client, email="taxcalc1@test.com")
    cfg = await _create_config(client, token, year=2025, gross=30000)

    resp = await client.get(
        f"/api/v1/tax/configs/{cfg['id']}/calculation", headers=_auth(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    for key in [
        "tax_year",
        "gross_annual",
        "ss_annual",
        "ss_rate",
        "work_expenses_deduction",
        "taxable_base",
        "irpf_annual",
        "effective_rate",
        "net_annual",
        "net_monthly",
        "bracket_breakdown",
    ]:
        assert key in data


async def test_calculation_net_monthly_consistency(client: AsyncClient):
    """net_monthly should be approximately net_annual / 12."""
    token = await _register_and_token(client, email="taxcalc2@test.com")
    cfg = await _create_config(client, token, year=2025, gross=30000)

    resp = await client.get(
        f"/api/v1/tax/configs/{cfg['id']}/calculation", headers=_auth(token)
    )
    data = resp.json()
    assert float(data["net_monthly"]) == pytest.approx(float(data["net_annual"]) / 12, abs=0.02)


async def test_calculation_ss_2025_rate(client: AsyncClient):
    """SS rate for 2025 must be 6.35 %."""
    token = await _register_and_token(client, email="taxcalc3@test.com")
    cfg = await _create_config(client, token, year=2025, gross=30000)

    resp = await client.get(
        f"/api/v1/tax/configs/{cfg['id']}/calculation", headers=_auth(token)
    )
    data = resp.json()
    assert float(data["ss_rate"]) == pytest.approx(0.0635, abs=0.0001)


async def test_calculation_ss_capped_at_max_base(client: AsyncClient):
    """For a very high salary, SS should be capped at max base × 12 × rate."""
    token = await _register_and_token(client, email="taxcalc4@test.com")
    cfg = await _create_config(client, token, year=2025, gross=200000)

    resp = await client.get(
        f"/api/v1/tax/configs/{cfg['id']}/calculation", headers=_auth(token)
    )
    data = resp.json()
    # max_base_monthly=4909.50, rate=6.35% → max SS = 4909.50*12*0.0635 ≈ 3 740.45
    expected_max_ss = 4909.50 * 12 * 0.0635
    assert float(data["ss_annual"]) == pytest.approx(expected_max_ss, abs=0.5)


async def test_calculation_effective_rate_in_range(client: AsyncClient):
    """Effective IRPF rate for 30k gross should be between 5% and 20%."""
    token = await _register_and_token(client, email="taxcalc5@test.com")
    cfg = await _create_config(client, token, year=2025, gross=30000)

    resp = await client.get(
        f"/api/v1/tax/configs/{cfg['id']}/calculation", headers=_auth(token)
    )
    effective = float(resp.json()["effective_rate"])
    assert 5.0 <= effective <= 20.0


async def test_calculation_bracket_breakdown_has_entries(client: AsyncClient):
    token = await _register_and_token(client, email="taxcalc6@test.com")
    cfg = await _create_config(client, token, year=2025, gross=50000)

    resp = await client.get(
        f"/api/v1/tax/configs/{cfg['id']}/calculation", headers=_auth(token)
    )
    breakdown = resp.json()["bracket_breakdown"]
    assert len(breakdown) >= 2  # 50k hits multiple brackets


async def test_calculation_work_expenses_deduction(client: AsyncClient):
    """Work expenses deduction must be 2000 €."""
    token = await _register_and_token(client, email="taxcalc7@test.com")
    cfg = await _create_config(client, token, year=2025, gross=30000)

    resp = await client.get(
        f"/api/v1/tax/configs/{cfg['id']}/calculation", headers=_auth(token)
    )
    assert float(resp.json()["work_expenses_deduction"]) == pytest.approx(2000.0, abs=0.01)


async def test_calculation_high_salary_higher_effective_rate(client: AsyncClient):
    """Higher gross → higher effective IRPF rate (progressive system)."""
    token = await _register_and_token(client, email="taxprog@test.com")
    cfg_low = await _create_config(client, token, year=2025, gross=20000)
    cfg_high = await _create_config(client, token, year=2026, gross=80000)

    r_low = await client.get(
        f"/api/v1/tax/configs/{cfg_low['id']}/calculation", headers=_auth(token)
    )
    r_high = await client.get(
        f"/api/v1/tax/configs/{cfg_high['id']}/calculation", headers=_auth(token)
    )

    rate_low = float(r_low.json()["effective_rate"])
    rate_high = float(r_high.json()["effective_rate"])
    assert rate_high > rate_low


# ── Integration: mortgage affordability with tax_config_id ────────────────────


async def test_affordability_uses_tax_net_income(client: AsyncClient):
    """When tax_config_id is passed, affordability uses net monthly salary."""
    token = await _register_and_token(client, email="taxafford@test.com")
    cfg = await _create_config(client, token, year=2025, gross=36000)

    # Get the net_monthly from the tax calculation
    calc_resp = await client.get(
        f"/api/v1/tax/configs/{cfg['id']}/calculation", headers=_auth(token)
    )
    net_monthly = float(calc_resp.json()["net_monthly"])

    # Call affordability with tax_config_id
    aff_resp = await client.get(
        f"/api/v1/mortgage/affordability?tax_config_id={cfg['id']}",
        headers=_auth(token),
    )
    assert aff_resp.status_code == 200
    data = aff_resp.json()
    assert float(data["monthly_net_income"]) == pytest.approx(net_monthly, abs=0.02)
    assert float(data["max_monthly_payment"]) == pytest.approx(net_monthly * 0.35, abs=0.5)
