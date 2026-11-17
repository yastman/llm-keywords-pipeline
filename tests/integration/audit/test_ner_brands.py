"""Tests for audit/ner_brands.py"""

import pytest

from llm_keywords_pipeline.audit import ner_brands
from llm_keywords_pipeline.audit.ner_brands import (
    check_blacklist,
    is_false_positive_location,
)


def test_ner_unavailable_warning_names_uv(monkeypatch):
    """Without full Natasha, check_ner's warning names the uv command."""
    monkeypatch.setattr(ner_brands, "NATASHA_FULL", False)
    result = ner_brands.check_ner("Текст.")
    assert result["ner_entities"] == []
    assert "uv sync --group nlp" in result["warning"]


@pytest.mark.usefixtures("ultimate_root")
class TestBrandBlacklist:
    """Tests for brand blacklist checks ([blacklist] brands of the car-care project.toml)."""

    def test_detects_brand_koch(self):
        """Should detect Koch Chemie brand."""
        text = "Это средство от Koch Chemie отлично работает"
        result = check_blacklist(text)
        assert len(result["brands"]) > 0

    def test_detects_brand_grass(self):
        """Should detect Grass brand."""
        text = "Активная пена Grass для бесконтактной мойки"
        result = check_blacklist(text)
        assert len(result["brands"]) > 0

    def test_brand_inside_word_not_flagged_ru(self):
        """'ауди' inside 'аудиосистемы' is not the brand Audi."""
        text = "Протрите пластик аудиосистемы мягкой микрофиброй"
        result = check_blacklist(text)
        assert result["brands"] == []

    def test_brand_inside_word_not_flagged_uk(self):
        """'ауди' inside 'аудіосистема'/'аудиторія' is not the brand Audi."""
        text = "Протріть пластик аудиосистеми, це оцінить аудиторія"
        result = check_blacklist(text)
        assert result["brands"] == []

    def test_brand_as_word_flagged_ru(self):
        text = "Полироль подходит для Ауди и других авто"
        result = check_blacklist(text)
        assert [b["entity"] for b in result["brands"]] == ["ауди"]

    def test_brand_as_word_flagged_uk(self):
        text = "Поліроль підходить для Ауди та інших авто"
        result = check_blacklist(text)
        assert [b["entity"] for b in result["brands"]] == ["ауди"]

    def test_no_brands_in_clean_text(self):
        """Clean text should have no brands."""
        text = "Активная пена для бесконтактной мойки автомобиля"
        result = check_blacklist(text)
        assert len(result["brands"]) == 0


class TestCityBlacklist:
    """Tests for city blacklist checks."""

    def test_detects_city_kiev(self):
        """Should detect Kiev city."""
        text = "Доставка по Киеву и области"
        result = check_blacklist(text)
        assert len(result["cities"]) > 0

    def test_detects_uk_city_case_forms(self):
        """UK oblique forms (Києву, Харкову, Тернополю) are caught by lemma."""
        text = "Доставка по Києву, Харкову та Тернополю"
        result = check_blacklist(text)
        # one finding per word, though "тернополю" has a UK and a RU city lemma
        assert sorted(c["entity"] for c in result["cities"]) == ["київ", "тернопіль", "харків"]

    def test_ru_city_form_reported_once(self):
        """'Киеву' has the 'киев' stem and a city parse; it is reported once."""
        result = check_blacklist("Доставка по Киеву")
        assert [c["entity"] for c in result["cities"]] == ["киев"]

    def test_uk_lemma_false_positive_city_skipped(self):
        """Lowercase 'сумах' reads as 'суми' and 'сума'; it is not the city."""
        text = "Ціни в гривнях і різних сумах"
        result = check_blacklist(text)
        assert result["cities"] == []

    def test_detects_uk_locative_city(self):
        """'Києві': first UK parse is 'кий', the city parse 'київ' must still count."""
        result = check_blacklist("Доставка у Києві.")
        assert [c["entity"] for c in result["cities"]] == ["київ"]

    def test_uk_capitalized_ambiguous_city_counts(self):
        """A capitalized form with a common-word reading (Сумах, Рівному) is the city."""
        result = check_blacklist("Доставка в Сумах і у Рівному")
        assert sorted(c["entity"] for c in result["cities"]) == ["рівне", "суми"]

    def test_uk_city_without_location_preposition(self):
        """'по Рівному' and cities in a list after 'та'/',' are caught."""
        result = check_blacklist("Доставка у Києві та Рівному.")
        assert sorted(c["entity"] for c in result["cities"]) == ["київ", "рівне"]
        result = check_blacklist("Офіс у Києві та Харкові")
        assert sorted(c["entity"] for c in result["cities"]) == ["київ", "харків"]
        result = check_blacklist("Працюємо в Києві, Миколаєві, Черкасах і Луцьку")
        assert sorted(c["entity"] for c in result["cities"]) == [
            "київ",
            "луцьк",
            "миколаїв",
            "черкаси",
        ]

    def test_uk_city_name_not_surname_parse(self):
        """Surname readings ('львов', 'харко') neither become the city nor make it ambiguous."""
        assert [c["entity"] for c in check_blacklist("Магазин у Львові")["cities"]] == ["львів"]
        assert [c["entity"] for c in check_blacklist("магазин у харкові")["cities"]] == ["харків"]

    def test_uk_lowercase_common_word_not_city(self):
        """Lowercase 'рівним/рівного' (no location preposition) and 'у сумах' (vetoed) are not cities."""
        text = "Нанесіть рівним шаром на рівну поверхню, рівного кольору"
        assert check_blacklist(text)["cities"] == []
        assert check_blacklist("У сумах до 1000 грн")["cities"] == []

    def test_rovno_adverb_not_city(self):
        assert check_blacklist("Отрежьте ровно половину")["cities"] == []

    def test_sentence_initial_homograph_not_city(self):
        """A capital letter that only opens a sentence is no city signal."""
        assert check_blacklist("Рівним шаром нанесіть засіб.")["cities"] == []
        assert check_blacklist("Готово. Рівним шаром нанесіть засіб.")["cities"] == []
        assert check_blacklist("- Рівним шаром нанесіть засіб.")["cities"] == []

    def test_lowercase_city_after_preposition(self):
        """A location preposition makes a lowercase ambiguous form a city."""
        assert [c["entity"] for c in check_blacklist("доставка у києві")["cities"]] == ["київ"]
        result = check_blacklist("поехал в ровно на машине")
        assert [c["entity"] for c in result["cities"]] == ["ровно"]

    def test_lowercase_city_list_after_preposition(self):
        """Cities in a list after ',' / 'та' / 'і' inherit the preposition of the first."""
        result = check_blacklist("доставка у києві та рівному")
        assert sorted(c["entity"] for c in result["cities"]) == ["київ", "рівне"]
        result = check_blacklist("доставка по києву, харкову та тернополю")
        assert sorted(c["entity"] for c in result["cities"]) == ["київ", "тернопіль", "харків"]
        # no preposition before the list: no city
        assert check_blacklist("ціна києві та рівному")["cities"] == []

    def test_lowercase_false_positive_form_vetoed_after_preposition(self):
        """Lowercase 'сумах' (FALSE_POSITIVE_CITIES) after 'у' stays amounts; capitalised is the city."""
        assert check_blacklist("ціни у сумах до 1000 грн")["cities"] == []
        assert [c["entity"] for c in check_blacklist("ціни у Сумах")["cities"]] == ["суми"]
        assert [c["entity"] for c in check_blacklist("Доставка в Сумах")["cities"]] == ["суми"]

    def test_lowercase_form_after_na_not_city(self):
        """'на' alone before a lowercase form is no place; any other case after 'на' counts."""
        assert check_blacklist("на ровном месте")["cities"] == []
        assert check_blacklist("Працюйте на рівному майданчику")["cities"] == []
        # ALL-CAPS after a preposition counts, "на" included (the copy cannot tell them apart)
        result = check_blacklist("ПРАЦЮЙТЕ НА РІВНОМУ МАЙДАНЧИКУ")
        assert [c["entity"] for c in result["cities"]] == ["рівне"]
        assert [c["entity"] for c in check_blacklist("ДОСТАВКА НА РІВНЕ")["cities"]] == ["рівне"]
        assert [c["entity"] for c in check_blacklist("Доставка на Київ")["cities"]] == ["київ"]
        assert [c["entity"] for c in check_blacklist("Доставка на Рівне")["cities"]] == ["рівне"]
        # other prepositions keep any case
        assert [c["entity"] for c in check_blacklist("ДОСТАВКА У РІВНЕ")["cities"]] == ["рівне"]

    def test_lowercase_sumy_vetoed_after_preposition(self):
        """Lowercase 'суми' after a preposition is an amount; 'в ровно' stays a city."""
        assert check_blacklist("Знижка діє до суми замовлення 1000 грн")["cities"] == []
        assert check_blacklist("на суми понад 500 грн")["cities"] == []
        result = check_blacklist("поехал в ровно на машине")
        assert [c["entity"] for c in result["cities"]] == ["ровно"]

    def test_city_abbreviation_before_city(self):
        """'м.'/'г.' is no sentence end and is transparent for the preposition."""
        assert [c["entity"] for c in check_blacklist("Офіс у м. Києві")["cities"]] == ["київ"]
        assert [c["entity"] for c in check_blacklist("офіс у м. києві")["cities"]] == ["київ"]
        # 'кг.' is no one-letter abbreviation: it ends the sentence
        assert check_blacklist("Ціна за кг. Рівним шаром нанесіть.")["cities"] == []
        # no preposition reaches the city: only the sentence rule sees 'м.'
        result = check_blacklist("Адреса: м. Рівне, вул. Соборна")
        assert [c["entity"] for c in result["cities"]] == ["рівне"]

    def test_unit_after_number_ends_sentence(self):
        """'5 м.' / '50 г.' is a unit, not a city abbreviation."""
        assert check_blacklist("Довжина 5 м. Рівним шаром нанесіть пасту.")["cities"] == []
        assert check_blacklist("Візьміть 50 г. Рівним шаром нанесіть.")["cities"] == []

    def test_all_caps_and_table_cell_not_city(self):
        """An ALL-CAPS word is no capital-letter signal; '|' opens a table cell."""
        assert check_blacklist("## НАНЕСІТЬ РІВНИМ ШАРОМ")["cities"] == []
        assert check_blacklist("| Спосіб | Рівним шаром |")["cities"] == []

    def test_no_cities_in_clean_text(self):
        """Clean text should have no cities."""
        text = "Доставка по всей Украине"
        result = check_blacklist(text)
        # May have false positives for "украине" but not cities
        # Check specifically for city entities
        city_names = [c["entity"] for c in result["cities"]]
        assert "киев" not in city_names


class TestFalsePositiveLocation:
    """Tests for false positive detection."""

    def test_rovno_as_adverb_is_false_positive(self):
        """'ровно' as adverb should be false positive."""
        # Without preposition - should be false positive
        result = is_false_positive_location("ровно", "занимает ровно 5 минут")
        assert result is True

    def test_rovno_with_preposition_is_real_city(self):
        """'в ровно' should be detected as real city."""
        result = is_false_positive_location("ровно", "доставка в Ровно")
        assert result is False


class TestAIFluff:
    """Tests for AI fluff detection."""

    def test_detects_ai_fluff_phrase(self):
        """Should detect AI fluff phrases."""
        text = "В этой статье мы рассмотрим особенности выбора"
        result = check_blacklist(text)
        assert len(result["ai_fluff"]) > 0

    def test_no_ai_fluff_in_clean_text(self):
        """Clean text should have no AI fluff."""
        text = "Активная пена создаёт густую плотную пену для мойки"
        result = check_blacklist(text)
        assert len(result["ai_fluff"]) == 0


class TestStrictPhrases:
    """Tests for strict blacklist phrases."""

    def test_detects_strict_phrase(self):
        """Should detect strict blacklist phrase."""
        text = "В современном мире автохимия стала необходимостью"
        result = check_blacklist(text)
        assert len(result["strict_phrases"]) > 0


UK_NER_TEXT = "Доставка по Києву, Харкову та Тернополю від компанії Нова Пошта."
RU_NER_TEXT = "Доставка по Киеву, Харькову и Тернополю от компании Новая Почта."


def _analyze_json(path, capsys) -> dict:
    import json

    ner_brands.analyze_file(str(path), output_json=True)
    return json.loads(capsys.readouterr().out)


def test_uk_file_runs_no_ru_ner(tmp_path, capsys):
    """UK file: natasha NER (RU-only) skipped, zero counts, no invented PER."""
    path = tmp_path / "uk" / "categories" / "test.md"
    path.parent.mkdir(parents=True)
    path.write_text(UK_NER_TEXT, encoding="utf-8")

    result = _analyze_json(path, capsys)

    assert result["ner"]["ner_entities"] == []
    assert result["ner"]["skipped"] is True
    assert "RU-only" in result["ner"]["warning"]
    assert result["summary"]["ner_per_count"] == 0
    assert result["summary"]["ner_loc_count"] == 0
    assert result["summary"]["ner_org_count"] == 0


def test_ru_file_still_runs_ner(tmp_path, capsys):
    path = tmp_path / "ru" / "categories" / "test.md"
    path.parent.mkdir(parents=True)
    path.write_text(RU_NER_TEXT, encoding="utf-8")

    result = _analyze_json(path, capsys)

    assert "skipped" not in result["ner"]
    assert result["summary"]["ner_loc_count"] == 3
    assert result["summary"]["ner_org_count"] == 1


def test_check_ner_lang_switch():
    assert ner_brands.check_ner(UK_NER_TEXT, "uk")["ner_entities"] == []
    assert ner_brands.check_ner(RU_NER_TEXT, "ru")["ner_entities"]
