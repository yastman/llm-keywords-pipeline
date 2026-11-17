"""Tests for generate/plural_sql.py"""

import json

import pytest

from llm_keywords_pipeline.generate import plural_sql
from llm_keywords_pipeline.generate.plural_sql import generate_plural_sql

OPENCART = '[opencart]\ntable_prefix = "oc_"\nlanguage_ids = { uk = 1, ru = 3 }\n'


def _setup(tmp_path, monkeypatch, slug_to_id, uk_meta=None, plural_ru=None, project_toml=OPENCART):
    root = tmp_path / "root"
    gen = root / "data" / "generated"
    gen.mkdir(parents=True)
    # Data root is PROJECT_ROOT, never the cwd
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(plural_sql, "PROJECT_ROOT", root)
    (root / "project.toml").write_text(project_toml, encoding="utf-8")
    (root / "data" / "opencart_mapping.json").write_text(json.dumps({"slug_to_id": slug_to_id}))
    (gen / "plural_manual_uk.json").write_text("{}")
    (gen / "plural_manual_ru.json").write_text(json.dumps(plural_ru or {}, ensure_ascii=False))
    for slug, meta in (uk_meta or {}).items():
        d = root / "uk" / "categories" / slug / "meta"
        d.mkdir(parents=True)
        (d / f"{slug}_meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    return root


def test_uk_values_escaped_with_escape_sql(tmp_path, monkeypatch):
    root = _setup(
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
    assert (root / "data" / "generated" / "plural_meta_update.sql").is_file()


@pytest.mark.parametrize(
    "meta",
    [
        {"h1": "H", "meta": {"title": "T"}},  # nested shape
        {"h1": "H", "title": "T", "description": "D"},  # top-level shape
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
        "meta_title='abc\\\\ — купить, цены' WHERE category_id=5 AND language_id=3;"
    ]


def test_ru_title_brand_from_project_toml_of_project_root(tmp_path, monkeypatch):
    _setup(
        tmp_path,
        monkeypatch,
        {"s": 5},
        plural_ru={"s": "Конфеты"},
        project_toml='[project]\nbrand = "Genesis"\n\n' + OPENCART,
    )
    # A project.toml in the cwd is not read
    (tmp_path / "elsewhere" / "project.toml").write_text(
        '[project]\nbrand = "Cwd"\n', encoding="utf-8"
    )

    assert generate_plural_sql() == [
        "UPDATE oc_category_description SET meta_h1='Конфеты', "
        "meta_title='Конфеты — купить, цены | Genesis' WHERE category_id=5 AND language_id=3;"
    ]


def test_table_prefix_and_language_ids_from_project_toml(tmp_path, monkeypatch):
    _setup(
        tmp_path,
        monkeypatch,
        {"s": 5},
        uk_meta={"s": {"h1": "H", "meta": {"title": "T"}}},
        plural_ru={"s": "R"},
        project_toml='[opencart]\ntable_prefix = "shop_"\nlanguage_ids = { uk = 2, ru = 7 }\n',
    )
    assert generate_plural_sql() == [
        "UPDATE shop_category_description SET meta_h1='H', meta_title='T' "
        "WHERE category_id=5 AND language_id=2;",
        "UPDATE shop_category_description SET meta_h1='R', meta_title='R — купить, цены' "
        "WHERE category_id=5 AND language_id=7;",
    ]


@pytest.mark.parametrize(
    ("project_toml", "key"),
    [
        ("", "[opencart] table_prefix"),
        ("[opencart]\nlanguage_ids = { uk = 1, ru = 3 }\n", "[opencart] table_prefix"),
        ('[opencart]\ntable_prefix = "oc_"\nlanguage_ids = { ru = 3 }\n', "language_ids.uk"),
        ('[opencart]\ntable_prefix = "oc_"\nlanguage_ids = { uk = 1 }\n', "language_ids.ru"),
    ],
)
def test_missing_opencart_key_stops_naming_it(tmp_path, monkeypatch, project_toml, key):
    _setup(tmp_path, monkeypatch, {"s": 5}, plural_ru={"s": "R"}, project_toml=project_toml)
    with pytest.raises(SystemExit) as exc:
        generate_plural_sql()
    assert key in str(exc.value)


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
