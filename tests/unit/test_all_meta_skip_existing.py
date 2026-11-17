"""all_meta must never overwrite an existing meta file without --force (audit B4)."""

import json

import pytest

from llm_keywords_pipeline.generate import all_meta
from tests.conftest import ULTIMATE_PROJECT_TOML

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


@pytest.fixture
def ultimate_tree(tree):
    """Data root of `tree` with the car-care project.toml (brands skipped as types)."""
    (tree.parents[3] / "project.toml").write_bytes(ULTIMATE_PROJECT_TOML.read_bytes())
    return tree


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


def test_types_read_from_entity_dictionary(ultimate_tree):
    data = {"entity_dictionary": {"types": ["pad", "compound"], "brands": ["Koch polish"]}}
    assert all_meta.get_types_from_entities(data) == ["pad", "compound"]


def test_types_fall_back_to_old_entities_list(ultimate_tree):
    assert all_meta.get_types_from_entities({"entities": ["pad", "Rupes pad"]}) == ["pad"]


def test_types_skip_no_brand_without_config(tree):
    data = {"entity_dictionary": {"types": ["pad", "Koch polish"]}}
    assert all_meta.get_types_from_entities(data) == ["pad", "Koch polish"]


@pytest.mark.parametrize("lang", ["ru", "uk"])
def test_short_description_gets_neutral_filler(tree, lang):
    generator = all_meta.generate_meta_ru if lang == "ru" else all_meta.generate_meta_uk

    description = generator(SLUG, {"name": "тест", "keywords": [{"keyword": "тест ключ"}]})["meta"][
        "description"
    ]

    assert description.startswith("Тест. ")
    assert 100 <= len(description) <= 160


def test_long_description_gets_no_filler(tree):
    types = ["тип " + "а" * 50, "тип " + "б" * 50]

    description = all_meta.build_description("ru", "Тест ключ", "Тест", types)

    assert description == f"Тест. {types[0].capitalize()}, {types[1]}."


@pytest.mark.parametrize("lang", ["ru", "uk"])
def test_description_template_from_project_toml(tree, lang):
    root = tree.parents[3]
    (root / "project.toml").write_text(
        '[project]\nbrand = "Genesis"\n\n[meta]\n'
        f'description_template = {{ {lang} = "{{keyword}} оптом від {{brand}}. {{types}}." }}\n',
        encoding="utf-8",
    )
    generator = all_meta.generate_meta_ru if lang == "ru" else all_meta.generate_meta_uk
    data = {"name": "тест", "keywords": [{"keyword": "тест ключ"}], "entities": ["pad"]}

    meta = generator(SLUG, data)

    assert meta["meta"]["description"] == "Тест ключ оптом від Genesis. Pad."
