"""Tests for audit/ner_brands.py"""

from llm_keywords_pipeline.audit.ner_brands import (
    check_blacklist,
    is_false_positive_location,
)


class TestBrandBlacklist:
    """Tests for brand blacklist checks."""

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
        """'рівним/рівного' (adjective) and 'сумах' (amounts) in lowercase are not cities."""
        text = "Нанесіть рівним шаром на рівну поверхню, рівного кольору"
        assert check_blacklist(text)["cities"] == []
        assert check_blacklist("У сумах до 1000 грн")["cities"] == []

    def test_rovno_adverb_not_city(self):
        assert check_blacklist("Отрежьте ровно половину")["cities"] == []

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
