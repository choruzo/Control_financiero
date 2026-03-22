"""
Tests unitarios para app/ml/trainer.py.

Verifican las funciones puras del módulo sin necesidad de GPU ni modelo real.
"""

import json
import tempfile
from pathlib import Path

import pytest

from app.ml.trainer import (
    build_training_examples,
    get_next_version,
    load_base_dataset,
    train_val_split,
)


# ── get_next_version ──────────────────────────────────────────────────────────


def test_version_increment_basic():
    assert get_next_version("1.0") == "1.1"


def test_version_increment_double_digit():
    assert get_next_version("1.9") == "1.10"


def test_version_increment_major_preserved():
    assert get_next_version("2.3") == "2.4"


def test_version_increment_invalid_falls_back():
    assert get_next_version("invalid") == "1.1"


def test_version_increment_empty_falls_back():
    assert get_next_version("") == "1.1"


# ── build_training_examples ───────────────────────────────────────────────────


def test_build_examples_includes_base_dataset():
    """Sin feedback, solo devuelve el dataset base."""
    texts, labels = build_training_examples(feedback_items=[])
    assert len(texts) > 0
    assert len(texts) == len(labels)


def test_build_examples_adds_valid_feedback():
    """Feedback válido se añade al dataset base."""
    texts_base, _ = build_training_examples(feedback_items=[])
    base_count = len(texts_base)

    feedback = [
        {"description": "Compra MERCADONA", "correct_category_id": 0},
        {"description": "Taxi cabify", "correct_category_id": 1},
    ]
    texts, labels = build_training_examples(feedback_items=feedback)

    assert len(texts) == base_count + 2
    assert "Compra MERCADONA" in texts
    assert "Taxi cabify" in texts


def test_build_examples_skips_invalid_category():
    """Feedback con category_id fuera del rango se ignora."""
    texts_base, _ = build_training_examples(feedback_items=[])
    base_count = len(texts_base)

    feedback = [
        {"description": "Algo válido", "correct_category_id": 0},
        {"description": "Algo inválido", "correct_category_id": 999},
    ]
    texts, labels = build_training_examples(feedback_items=feedback)

    # Solo 1 nuevo ejemplo (el válido)
    assert len(texts) == base_count + 1


def test_build_examples_skips_empty_description():
    """Feedback con descripción vacía se ignora."""
    texts_base, _ = build_training_examples(feedback_items=[])
    base_count = len(texts_base)

    feedback = [{"description": "", "correct_category_id": 0}]
    texts, labels = build_training_examples(feedback_items=feedback)

    assert len(texts) == base_count


def test_build_examples_with_custom_dataset():
    """Funciona con un dataset personalizado pasado como path."""
    dataset = [
        {"text": "Supermercado", "label": "Alimentación"},
        {"text": "Bus metro", "label": "Transporte"},
    ]
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
        json.dump(dataset, f)
        tmp_path = Path(f.name)

    try:
        texts, labels = build_training_examples(feedback_items=[], base_dataset_path=tmp_path)
        assert len(texts) == 2
        assert "Supermercado" in texts
    finally:
        tmp_path.unlink()


# ── train_val_split ───────────────────────────────────────────────────────────


def test_train_val_split_ratio():
    """El split respeta aproximadamente el ratio 80/20."""
    texts = [f"tx{i}" for i in range(100)]
    labels = [i % 10 for i in range(100)]

    train_t, train_l, val_t, val_l = train_val_split(texts, labels, val_ratio=0.2)

    assert len(train_t) + len(val_t) == 100
    assert len(val_t) >= 10  # Al menos ~20% en validación


def test_train_val_split_no_empty_splits():
    """Incluso con pocos ejemplos, cada split tiene al menos 1 elemento."""
    texts = ["a", "b", "c"]
    labels = [0, 0, 1]

    train_t, train_l, val_t, val_l = train_val_split(texts, labels, val_ratio=0.5)

    assert len(train_t) >= 1
    assert len(val_t) >= 1
