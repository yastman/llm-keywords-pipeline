"""all_meta must never overwrite an existing meta file without --force (audit B4)."""

import json

import pytest

from llm_keywords_pipeline.generate import all_meta

SLUG = "test-cat"


@pytest.fixture
def tree(tmp_path, monkeypatch):
    monkeypatch.setattr(all_meta, "PROJECT_ROOT", tmp_path)
    cat = tmp_path / "categories" / SLUG
    (cat / "data").mkdir(parents=True)
    (cat / "meta").mkdir()
    clean = {"name": "тест", "keywords": [{"keyword": "тест ключ"}], "entities": []}
    (cat / "data" / f"{SLUG}_clean.json").write_text(
        json.dumps(clean, ensure_ascii=False), encoding="utf-8"
    )
    meta_file = cat / "meta" / f"{SLUG}_meta.json"
    # LLM-written meta: no types/volumes/keywords_in_content fields
    meta_file.write_text(
        '{"slug": "test-cat", "meta": {"title": "РУЧНОЙ title", "description": "x"}}',
        encoding="utf-8",
    )
    return meta_file


def test_existing_meta_untouched_without_force(tree):
    before = tree.read_bytes()
    generated, _, preserved = all_meta.process_categories(lang="ru")
    assert tree.read_bytes() == before
    assert (generated, preserved) == (0, 1)


def test_existing_meta_regenerated_with_force(tree):
    generated, _, _ = all_meta.process_categories(lang="ru", force=True)
    assert generated == 1
    meta = json.loads(tree.read_text(encoding="utf-8"))
    assert meta["meta"]["title"] == "Тест ключ — купить, цены"
    assert "производител" not in meta["meta"]["description"]
    assert "Опт" not in meta["meta"]["description"]


@pytest.mark.parametrize(
    ("lang", "title"),
    [("ru", "Тест ключ — купить, цены | Genesis"), ("uk", "Тест ключ — купити, ціни | Genesis")],
)
def test_brand_suffix_from_project_toml(tree, lang, title):
    root = tree.parents[3]
    (root / "project.toml").write_text('[project]\nbrand = "Genesis"\n', encoding="utf-8")
    generator = all_meta.generate_meta_ru if lang == "ru" else all_meta.generate_meta_uk

    meta = generator(SLUG, {"name": "тест", "keywords": [{"keyword": "тест ключ"}]})

    assert meta["meta"]["title"] == title
    assert "Ultimate" not in meta["meta"]["description"]


def test_missing_meta_generated_without_force(tree):
    tree.unlink()
    generated, _, _ = all_meta.process_categories(lang="ru")
    assert generated == 1
    assert tree.exists()


def test_types_read_from_entity_dictionary():
    data = {"entity_dictionary": {"types": ["pad", "compound"], "brands": ["Koch polish"]}}
    assert all_meta.get_types_from_entities(data) == ["pad", "compound"]


def test_types_fall_back_to_old_entities_list():
    assert all_meta.get_types_from_entities({"entities": ["pad", "Rupes pad"]}) == ["pad"]
