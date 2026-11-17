"""validate.meta requires client phrases only from <data root>/project.toml [meta]."""

import json

import pytest

from llm_keywords_pipeline.core import config
from llm_keywords_pipeline.validate.meta import validate_description, validate_meta_file

DISTRIBUTOR = {
    "uk": (
        "Шоколадні цукерки оптом від офіційного дистриб'ютора. "
        "Понад 500 позицій у наявності, доставка по всій Україні.",
        "шоколадні цукерки",
    ),
    "ru": (
        "Шоколадные конфеты оптом от официального дистрибьютора. "
        "Более 500 позиций в наличии, доставка по всей Украине.",
        "шоколадные конфеты",
    ),
}


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    return tmp_path


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_distributor_meta_passes_without_config(data_root, lang):
    desc, keyword = DISTRIBUTOR[lang]

    result = validate_description(desc, [keyword], lang=lang)

    assert result["overall"] == "PASS", result["checks"]


@pytest.mark.parametrize("lang", ["uk", "ru"])
def test_distributor_meta_file_passes_without_config(data_root, lang):
    desc, keyword = DISTRIBUTOR[lang]
    meta_file = data_root / "m_meta.json"
    meta = {"h1": keyword, "meta": {"title": f"{keyword} — ціни", "description": desc}}
    meta_file.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    result = validate_meta_file(str(meta_file), lang=lang)

    assert result["description"]["overall"] == "PASS"


def test_configured_phrase_missing_fails_by_name(data_root):
    (data_root / "project.toml").write_text(
        '[meta]\nrequired_phrases = { uk = ["офіційн\\\\w+ дистриб\'ютор", "опт\\\\b"] }\n',
        encoding="utf-8",
    )
    desc = (
        "Шоколадні цукерки: опт і поштучно у магазині. "
        "Понад 500 позицій у наявності, доставка по всій Україні та швидка відправка."
    )

    result = validate_description(desc, ["шоколадні цукерки"], lang="uk")

    assert result["overall"] == "FAIL"
    messages = " ".join(c["message"] for c in result["checks"].values())
    assert "офіційн\\w+ дистриб'ютор" in messages
    assert "опт\\b" not in messages


def test_configured_phrase_present_passes(data_root):
    (data_root / "project.toml").write_text(
        '[meta]\nrequired_phrases = { uk = ["офіційн\\\\w+ дистриб\'ютор"] }\n',
        encoding="utf-8",
    )
    desc, keyword = DISTRIBUTOR["uk"]

    assert validate_description(desc, [keyword], lang="uk")["overall"] == "PASS"


def test_configured_phrases_apply_per_language(data_root):
    (data_root / "project.toml").write_text(
        '[meta]\nrequired_phrases = { uk = ["відсутня фраза"] }\n', encoding="utf-8"
    )
    desc, keyword = DISTRIBUTOR["ru"]

    assert validate_description(desc, [keyword], lang="ru")["overall"] == "PASS"


def test_required_phrase_matches_capitalised_text(data_root):
    (data_root / "project.toml").write_text(
        '[meta]\nrequired_phrases = { uk = ["офіційн\\\\w+ дистриб\'ютор"] }\n', encoding="utf-8"
    )
    desc, keyword = DISTRIBUTOR["uk"]
    desc = desc.replace("офіційного дистриб'ютора", "Офіційного Дистриб'ютора")

    result = validate_description(desc, [keyword], lang="uk")

    assert result["checks"]["required_phrases"]["passed"], result["checks"]
    assert result["overall"] == "PASS"


def test_missing_recommended_phrase_warns(data_root):
    (data_root / "project.toml").write_text(
        '[meta]\nrecommended_phrases = { uk = ["роздріб"] }\n', encoding="utf-8"
    )
    desc, keyword = DISTRIBUTOR["uk"]

    result = validate_description(desc, [keyword], lang="uk")

    assert result["overall"] == "WARNING"
    assert result["checks"]["recommended_phrases"]["message"] == (
        "Missing recommended phrases: роздріб"
    )


def test_present_recommended_phrase_passes_case_insensitive(data_root):
    (data_root / "project.toml").write_text(
        '[meta]\nrecommended_phrases = { uk = ["понад \\\\d+ позиц"] }\n', encoding="utf-8"
    )
    desc, keyword = DISTRIBUTOR["uk"]

    result = validate_description(desc, [keyword], lang="uk")

    assert result["checks"]["recommended_phrases"]["passed"]
    assert result["overall"] == "PASS"
