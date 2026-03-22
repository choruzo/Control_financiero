"""
Tests del módulo ML: categories, preprocessor y ModelManager.

Los tests del ModelManager con inferencia real se saltan si el modelo
no está entrenado (directorio /app/models/categorizer/ no existe).
"""

from __future__ import annotations

import pytest


# ── Catálogo de categorías ───────────────────────────────────────────────────

class TestCategories:
    def test_num_labels_is_ten(self):
        from app.ml.categories import NUM_LABELS
        assert NUM_LABELS == 10

    def test_label_to_index_and_back(self):
        from app.ml.categories import INDEX_TO_LABEL, LABEL_TO_INDEX
        for name, idx in LABEL_TO_INDEX.items():
            assert INDEX_TO_LABEL[idx] == name

    def test_expected_categories_present(self):
        from app.ml.categories import LABEL_TO_INDEX
        expected = {
            "Alimentación", "Transporte", "Ocio", "Hogar", "Salud",
            "Educación", "Ropa", "Tecnología", "Ingresos", "Otros",
        }
        assert expected == set(LABEL_TO_INDEX.keys())

    def test_indices_are_consecutive(self):
        from app.ml.categories import CATEGORIES
        indices = [c["index"] for c in CATEGORIES]
        assert sorted(indices) == list(range(len(CATEGORIES)))

    def test_category_names_list(self):
        from app.ml.categories import CATEGORY_NAMES, NUM_LABELS
        assert len(CATEGORY_NAMES) == NUM_LABELS
        assert all(isinstance(n, str) for n in CATEGORY_NAMES)


# ── Preprocesador ────────────────────────────────────────────────────────────

class TestPreprocessor:
    def test_preserves_case(self):
        """El modelo fue entrenado con mayúsculas — no se convierte a minúsculas."""
        from app.ml.preprocessor import normalize_banking_text
        assert normalize_banking_text("MERCADONA SA") == "MERCADONA SA"

    def test_removes_long_numeric_references(self):
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("TRF 123456789 CONCEPTO")
        assert "123456789" not in result
        assert "CONCEPTO" in result

    def test_removes_dates(self):
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("PAGO 15/03/2024 MERCADONA")
        assert "15/03/2024" not in result
        assert "MERCADONA" in result

    def test_collapses_whitespace(self):
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("  MUCHO   ESPACIO  ")
        assert "  " not in result
        assert result == result.strip()

    def test_preserves_spanish_characters(self):
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("CAFÉ CON LECHE")
        assert "CAF" in result

    def test_short_numbers_kept(self):
        """Números cortos (< 6 dígitos) no se eliminan."""
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("PARKING 3 HORAS 2024")
        assert "3" in result

    def test_removes_banking_prefix_rec_dom(self):
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("REC DOM 20260201 IBERDROLA")
        assert "REC" not in result or "IBERDROLA" in result
        assert "IBERDROLA" in result

    def test_removes_banking_prefix_trf(self):
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("TRF 20260115 NOMINA EMPRESA")
        assert "NOMINA" in result
        assert "20260115" not in result

    def test_removes_banking_prefix_cobro_tpv(self):
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("COBRO TPV 987654321 REPSOL")
        assert "REPSOL" in result
        assert "987654321" not in result

    def test_removes_compact_dates(self):
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("DOM RECIBO 20250301 ENDESA")
        assert "20250301" not in result
        assert "ENDESA" in result

    def test_empty_string(self):
        from app.ml.preprocessor import normalize_banking_text
        assert normalize_banking_text("") == ""

    def test_only_special_chars(self):
        from app.ml.preprocessor import normalize_banking_text
        result = normalize_banking_text("*** --- ###")
        assert result == "" or result.strip() == ""


# ── ModelManager en modo degradado ──────────────────────────────────────────

class TestModelManagerDegraded:
    """Pruebas con ModelManager sin modelo en disco (modo degradado)."""

    @pytest.fixture
    def manager(self, tmp_path):
        from app.ml.model_manager import ModelManager
        return ModelManager(model_path=str(tmp_path), device="cpu")

    @pytest.mark.asyncio
    async def test_load_nonexistent_model_does_not_raise(self, manager):
        await manager.load()
        assert manager.loaded is False

    @pytest.mark.asyncio
    async def test_predict_degraded_returns_otros(self, manager):
        await manager.load()
        category, confidence = manager.predict("MERCADONA SA COMPRA")
        assert category == "Otros"
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_get_status_degraded(self, manager):
        await manager.load()
        status = manager.get_status()
        assert status["loaded"] is False
        assert status["version"] is None
        assert status["accuracy"] is None
        assert status["last_trained"] is None
        assert status["feedback_count"] == 0

    @pytest.mark.asyncio
    async def test_predict_empty_string_degraded(self, manager):
        await manager.load()
        category, confidence = manager.predict("")
        assert category == "Otros"
        assert confidence == 0.0


# ── Endpoint /health con modelo no cargado ───────────────────────────────────

@pytest.mark.asyncio
async def test_health_reports_model_not_loaded(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["model_loaded"] is False


@pytest.mark.asyncio
async def test_model_status_degraded_via_api(client):
    response = await client.get("/model/status")
    assert response.status_code == 200
    data = response.json()
    assert data["loaded"] is False
    assert data["feedback_count"] == 0
