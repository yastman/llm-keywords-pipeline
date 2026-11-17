"""Tests for generate/plural_sql.py"""

import json

import pytest

from llm_keywords_pipeline.generate.plural_sql import generate_plural_sql


def _setup(tmp_path, monkeypatch, slug_to_id, uk_meta=None, plural_ru=None):
    monkeypatch.chdir(tmp_path)
    gen = tmp_path / "data" / "generated"
    gen.mkdir(parents=True)
    (tmp_path / "data" / "opencart_mapping.json").write_text(json.dumps({"slug_to_id": slug_to_id}))
    (gen / "plural_manual_uk.json").write_text("{}")
    (gen / "plural_manual_ru.json").write_text(json.dumps(plural_ru or {}, ensure_ascii=False))
    for slug, meta in (uk_meta or {}).items():
        d = tmp_path / "uk" / "categories" / slug / "meta"
        d.mkdir(parents=True)
        (d / f"{slug}_meta.json").write_text(json.dumps(meta, ensure_ascii=False))


def test_uk_values_escaped_with_escape_sql(tmp_path, monkeypatch):
    _setup(
        tmp_path,
        monkeypatch,
        {"s": 5},
        uk_meta={"s": {"h1": "abc\\", "meta": {"title": 'it\'s "x"'}}},
    )
    lines = generate_plural_sql()
    assert lines == [
        "UPDATE oc_category_description SET meta_h1='abc\\\\', meta_title='it\\'s \\\"x\\\"' "
        "WHERE category_id=5 AND language_id=1;"
    ]


@pytest.mark.parametrize(
    "meta",
    [
        {"h1": "H", "meta": {"title": "T"}},  # nested shape
        {"h1": "H", "title": "T", "description": "D"},  # top-level shape (prompts/produce.md)
    ],
)
def test_uk_title_read_from_both_meta_shapes(tmp_path, monkeypatch, meta):
    _setup(tmp_path, monkeypatch, {"s": 5}, uk_meta={"s": meta})
    assert generate_plural_sql() == [
        "UPDATE oc_category_description SET meta_h1='H', meta_title='T' "
        "WHERE category_id=5 AND language_id=1;"
    ]


def test_ru_values_escaped_with_escape_sql(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {"s": 5}, plural_ru={"s": "abc\\"})
    lines = generate_plural_sql()
    assert lines == [
        "UPDATE oc_category_description SET meta_h1='abc\\\\', "
        "meta_title='abc\\\\ — купить, цены | Ultimate' WHERE category_id=5 AND language_id=3;"
    ]


def test_uk_non_numeric_cat_id_raises(tmp_path, monkeypatch):
    _setup(
        tmp_path, monkeypatch, {"s": "1 OR 1=1"}, uk_meta={"s": {"h1": "h", "meta": {"title": "t"}}}
    )
    with pytest.raises(ValueError):
        generate_plural_sql()


def test_ru_non_numeric_cat_id_raises(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {"s": "1 OR 1=1"}, plural_ru={"s": "h"})
    with pytest.raises(ValueError):
        generate_plural_sql()
