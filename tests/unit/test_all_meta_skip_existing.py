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
    assert meta["meta"]["title"] == "Тест ключ — купить, цены | Ultimate"


def test_missing_meta_generated_without_force(tree):
    tree.unlink()
    generated, _, _ = all_meta.process_categories(lang="ru")
    assert generated == 1
    assert tree.exists()
