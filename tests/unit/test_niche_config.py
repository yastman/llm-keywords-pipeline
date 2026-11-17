"""Niche rules come from <data root>/project.toml; an empty data root applies none (lkp-qml.3).

`data_root` is a data root without project.toml; `ultimate_root` holds the old car-care
rules (tests/fixtures/project_ultimate.toml). Both fixtures live in tests/conftest.py.
"""

import json

import pytest

from llm_keywords_pipeline.core import seo
from llm_keywords_pipeline.core.project import ProjectConfigError, load_project

SWEETS_RU = """# Шоколадные конфеты оптом

Шоколадные конфеты оптом для магазинов и кофеен: ассортимент фабрик Украины.

## Как выбрать шоколадные конфеты

Смотрите на состав, срок годности и фасовку. Конфеты в коробках подходят для подарков,
весовые для витрины.

## Частые вопросы

**Есть ли минимальный заказ?** Да, от одной коробки.
"""


def _toml(root, body):
    (root / "project.toml").write_text(body, encoding="utf-8")
    load_project.cache_clear()  # tests below read the same root before and after writing


# --- loader ---------------------------------------------------------------------------


def test_empty_config_has_no_niche_rules(data_root):
    project = load_project(data_root)

    assert project.slugs == {}
    assert project.commercial_markers == {}
    assert project.synonym_commercial_markers == ()
    assert project.meta_type_skip_brands == ()
    assert project.synonym_strip_terms == ()
    assert project.synonym_map == {}
    assert project.synonym_stems == {}
    assert project.blacklist_brands == ()
    assert project.blacklist_cities is True
    assert project.phrases_allow == ()
    assert project.category_substrings == {}
    assert project.l2_forbidden == {}
    assert not any(project.content_standards.values())
    assert project.tone == ""
    assert project.recommended_phrases == {}
    assert project.description_template == {}


def test_ultimate_fixture_parses(ultimate_root):
    project = load_project(ultimate_root)

    assert project.slugs["ru"]["Активная пена"] == "aktivnaya-pena"
    assert project.slugs["uk"]["Активна піна"] == "aktivnaya-pena"
    assert "koch" in project.blacklist_brands
    assert project.category_substrings["ru"]["aktivnaya-pena"] == (
        ("пен", "активн"),
        ("ручн", "шампун"),
    )
    assert all(project.content_standards.values())


@pytest.mark.parametrize(
    "body",
    [
        '[slugs]\nru = "x"\n',
        "[slugs.ru]\nx = 1\n",
        '[markers]\ncommercial = ["купить"]\n',
        '[synonyms]\nstrip_terms = "авто"\n',
        "[synonyms]\nmap = { a = 1 }\n",
        "[blacklist]\nbrands = [1]\n",
        '[synonyms]\ncommercial_markers = "киев"\n',
        '[meta]\ntype_skip_brands = "rupes"\n',
        '[blacklist]\ncities = "off"\n',
        '[blacklist]\nphrases_allow = "x"\n',
        '[density.category_substrings.ru]\nx = ["a"]\n',
        "[density.category_substrings.ru]\nx = { primary = [1] }\n",
        '[structure.l2_forbidden]\nx = ["(a"]\n',
        "[content_standards]\nsafety = true\n",
        '[content_standards]\nsafety_block = "yes"\n',
        "[niche]\ntone = 1\n",
        '[meta]\nrecommended_phrases = { uk = ["(опт"] }\n',
        '[meta]\ndescription_template = { uk = "{nope}" }\n',
    ],
)
def test_wrong_niche_value_names_the_file(tmp_path, body):
    _toml(tmp_path, body)

    with pytest.raises(ProjectConfigError, match=str(tmp_path / "project.toml")):
        load_project(tmp_path)


# --- slugs (core.seo) -----------------------------------------------------------------


@pytest.mark.parametrize("lang", ["ru", "uk"])
def test_empty_config_slugifies_category_names(data_root, lang):
    assert seo.get_mappings_for_lang(lang) == ({}, {})
    assert seo.slug_for("Активная пена", lang) == "aktivnaya-pena"
    assert seo.slug_for("Шоколадные конфеты", lang) == seo.slugify("Шоколадные конфеты")


def test_configured_slug_wins_over_slugify(data_root):
    _toml(data_root, '[slugs.uk]\n"Цукерки" = "konfety"\n')

    assert seo.slug_for("Цукерки", "uk") == "konfety"
    assert seo.slug_for("Цукерки", "ru") == seo.slugify("Цукерки")
    assert seo.get_mappings_for_lang("uk") == ({"Цукерки": "konfety"}, {"konfety": "Цукерки"})


# --- commercial markers ---------------------------------------------------------------


def test_commercial_markers_extend_generic_words(data_root):
    assert "купить" in seo.get_commercial_modifiers("ru")
    assert "оптом" not in seo.get_commercial_modifiers("uk")

    _toml(data_root, '[markers]\ncommercial = { uk = ["оптом"] }\n')

    assert "оптом" in seo.get_commercial_modifiers("uk")
    assert "купити" in seo.get_commercial_modifiers("uk")
    assert seo.get_commercial_modifiers("ru") == seo.COMMERCIAL_MODIFIERS


def test_core_synonyms_geo_marker_only_from_config(data_root):
    from llm_keywords_pipeline.core.synonyms import is_commercial

    assert is_commercial("купить пену")
    assert not is_commercial("пена киев")

    _toml(data_root, '[synonyms]\ncommercial_markers = ["киев"]\n')

    assert is_commercial("пена киев")


# --- synonyms -------------------------------------------------------------------------


def test_core_synonyms_strip_and_stems_from_config(data_root):
    from llm_keywords_pipeline.core.synonyms import normalize_keyword

    assert normalize_keyword("полировка для авто") == "авто полировка"

    _toml(data_root, '[synonyms]\nstrip_terms = ["для авто"]\nstems = { "полиров" = "полир" }\n')

    assert normalize_keyword("полировка для авто") == "полир"


def test_duplicates_synonym_map_from_config(data_root):
    from llm_keywords_pipeline.analyze.duplicates import normalize_keyword

    assert normalize_keyword("мойка машины") == "мойка машины"

    _toml(data_root, '[synonyms.map]\n"машины" = "авто"\n')

    assert normalize_keyword("мойка машины") == "мойка авто"


# --- brands, cities, strict phrases (audit.ner_brands) -------------------------------


def test_empty_config_has_no_car_care_brands(data_root):
    from llm_keywords_pipeline.audit.ner_brands import check_blacklist

    result = check_blacklist("Средство Koch Chemie и шампунь Sonax.", "ru")

    assert result["brands"] == []


def test_configured_brands_are_found(data_root):
    from llm_keywords_pipeline.audit.ner_brands import check_blacklist

    _toml(data_root, '[blacklist]\nbrands = ["Roshen"]\n')

    result = check_blacklist("Цукерки Roshen і Konti.", "uk")

    assert [b["entity"] for b in result["brands"]] == ["roshen"]


def test_city_check_on_by_default_and_off_by_config(data_root):
    from llm_keywords_pipeline.audit.ner_brands import check_blacklist

    text = "Доставка по Києву та у Харків."
    assert check_blacklist(text, "uk")["cities"]

    _toml(data_root, "[blacklist]\ncities = false\n")

    assert check_blacklist(text, "uk")["cities"] == []


def test_phrases_allow_drops_a_strict_phrase(data_root):
    from llm_keywords_pipeline.audit.ner_brands import check_blacklist

    text = "Широкий асортимент цукерок у сучасному світі."
    assert len(check_blacklist(text, "uk")["strict_phrases"]) == 2

    _toml(data_root, '[blacklist]\nphrases_allow = ["Широкий асортимент"]\n')

    found = [s["entity"] for s in check_blacklist(text, "uk")["strict_phrases"]]
    assert found == ["у сучасному світі"]


# --- density category substrings -------------------------------------------------------


def test_empty_config_has_no_category_substrings(data_root):
    from llm_keywords_pipeline.validate.density import analyze_text

    result = analyze_text("Активная пена для мойки.", slug="aktivnaya-pena", lang="ru")

    assert result["substring_analysis"] is None


def test_category_substrings_per_language(data_root):
    from llm_keywords_pipeline.validate.density import analyze_text

    _toml(
        data_root,
        '[density.category_substrings.uk]\ntsukerky = { primary = ["цукерк"], anti = ["печив"] }\n',
    )

    uk = analyze_text("Цукерки та цукерки, печиво.", slug="tsukerky", lang="uk")
    ru = analyze_text("Конфеты.", slug="tsukerky", lang="ru")

    assert uk["substring_analysis"]["primary"]["цукерк"]["count"] == 2
    assert uk["substring_analysis"]["anti"]["печив"]["count"] == 1
    assert ru["substring_analysis"] is None


# --- L2 forbidden (validate.structural) --------------------------------------------------


def _l2_category(root, monkeypatch, slug, keyword):
    from llm_keywords_pipeline.validate import structural

    monkeypatch.setattr(structural, "CATEGORIES_DIR", root / "categories")
    data_dir = root / "categories" / slug / "data"
    data_dir.mkdir(parents=True)
    data = {"type": "L2", "keywords": {"primary": [{"keyword": keyword}]}}
    (data_dir / f"{slug}_clean.json").write_text(json.dumps(data, ensure_ascii=False), "utf-8")
    return structural.check_category(slug)


def test_empty_config_has_no_l2_rule(data_root, monkeypatch):
    result = _l2_category(data_root, monkeypatch, "avtoshampuni", "шампунь для ручной мойки")

    assert result["status"] == "OK"


def test_l2_forbidden_from_config(data_root, monkeypatch):
    _toml(data_root, '[structure.l2_forbidden]\nkonfety = ["печив"]\n')

    result = _l2_category(data_root, monkeypatch, "konfety", "печиво оптом")

    assert result["issues"] == ["L2 Forbidden: 'печиво оптом' matches 'печив'"]


# --- content standards (validate.content) ----------------------------------------------


def test_sweets_text_has_no_content_standards_issue(data_root):
    from llm_keywords_pipeline.validate.content import check_content_standards

    result = check_content_standards(SWEETS_RU, lang="ru")

    assert result["issues"] == []
    assert result["overall"] == "OK"


def test_validate_content_sweets_text_no_content_standards_warning(data_root):
    from llm_keywords_pipeline.validate.content import validate_content

    md = data_root / "konfety_ru.md"
    md.write_text(SWEETS_RU, encoding="utf-8")

    result = validate_content(str(md), "шоколадные конфеты", mode="quality", lang="ru")

    assert result["checks"]["content_standards"]["issues"] == []
    assert "content_standards" not in result["summary"]["warnings"]


@pytest.mark.parametrize(
    ("key", "issue"),
    [
        ("safety_block", "Safety"),
        ("howto_steps", "How-to"),
        ("evergreen_math", "Evergreen Math"),
        ("warnings", "так не делайте"),
    ],
)
def test_each_content_standard_switch(data_root, key, issue):
    from llm_keywords_pipeline.validate.content import check_content_standards

    _toml(data_root, f"[content_standards]\n{key} = true\n")

    issues = check_content_standards(SWEETS_RU, lang="ru")["issues"]

    assert len(issues) == 1 and issue in issues[0]


def test_safety_switch_makes_warning(data_root):
    from llm_keywords_pipeline.validate.content import check_content_standards

    _toml(data_root, "[content_standards]\nsafety_block = true\n")

    assert check_content_standards(SWEETS_RU, lang="ru")["overall"] == "WARNING"


# --- editorial tone (analyze.category) -------------------------------------------------


def _brief(root, monkeypatch):
    from llm_keywords_pipeline.analyze import category

    monkeypatch.setattr(category, "PROJECT_ROOT", root)
    data_dir = root / "categories" / "konfety" / "data"
    data_dir.mkdir(parents=True)
    payload = {"keywords": {"primary": [{"keyword": "шоколадные конфеты", "volume": 100}]}}
    (data_dir / "konfety_clean.json").write_text(json.dumps(payload), encoding="utf-8")
    return category.analyze_category("konfety")


def test_empty_config_tone_is_neutral(data_root, monkeypatch):
    brief = json.dumps(_brief(data_root, monkeypatch), ensure_ascii=False)

    assert "детейлинг" not in brief
    assert "авто" not in brief


def test_tone_from_config(data_root, monkeypatch):
    _toml(data_root, '[niche]\ntone = "эксперт по сладостям"\n')

    brief = _brief(data_root, monkeypatch)

    assert brief["llm_prompt_hints"]["tone"] == "эксперт по сладостям"
    assert brief["content"]["quality"]["editorial_tone"] == "эксперт по сладостям"


# --- parity with the old per-consumer lists (car-care project.toml) ----------------------


def test_ultimate_geo_marker_is_synonyms_only(ultimate_root):
    from llm_keywords_pipeline.analyze.category import is_commercial_keyword
    from llm_keywords_pipeline.core.synonyms import is_commercial

    assert is_commercial("активная пена киев")
    assert not is_commercial_keyword("активная пена киев")
    assert seo.get_commercial_modifiers("ru") == seo.COMMERCIAL_MODIFIERS


def test_ultimate_audit_skips_all_meta_only_brands(ultimate_root):
    from llm_keywords_pipeline.audit.ner_brands import check_blacklist

    result = check_blacklist("Паста Menzerna, полироль Shiny и Koch Chemie.", "ru")

    assert sorted(b["entity"] for b in result["brands"]) == ["koch", "koch chemie"]


def test_ultimate_all_meta_skips_only_its_old_markers(ultimate_root, monkeypatch):
    from llm_keywords_pipeline.generate import all_meta

    monkeypatch.setattr(all_meta, "PROJECT_ROOT", ultimate_root)
    entities = ["Аудиосистемы", "Пена Grass", "Лаврушка", "Паста Menzerna", "Круг Rupes"]

    types = all_meta.get_types_from_entities({"entities": entities})

    assert types == ["Аудиосистемы", "Пена Grass", "Лаврушка"]
