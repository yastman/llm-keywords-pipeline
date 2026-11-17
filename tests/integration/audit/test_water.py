"""Tests for audit/water.py"""

from llm_keywords_pipeline.audit.water import calculate_metrics_from_text


class TestCalculateMetrics:
    """Tests for calculate_metrics_from_text function."""

    def test_returns_dict_with_required_keys(self):
        """Should return dict with all required metrics."""
        text = """
        Активная пена для бесконтактной мойки автомобиля.
        Создаёт густую плотную пену, которая эффективно удаляет грязь.
        Подходит для использования с пеногенератором или пенной насадкой.
        """
        result = calculate_metrics_from_text(text, lang="ru")

        assert result is not None
        assert "total_words" in result
        assert "water_percent" in result
        assert "classic_nausea" in result
        assert "academic_nausea" in result

    def test_water_percent_is_positive(self):
        """Water percent should be positive for normal text."""
        text = "Активная пена для бесконтактной мойки автомобиля удаляет грязь"
        result = calculate_metrics_from_text(text, lang="ru")

        assert result is not None
        assert result["water_percent"] >= 0

    def test_classic_nausea_is_positive(self):
        """Classic nausea should be positive."""
        text = "Пена пена пена для мойки пена автомобиля пена"
        result = calculate_metrics_from_text(text, lang="ru")

        assert result is not None
        assert result["classic_nausea"] > 0

    def test_empty_text_returns_none(self):
        """Empty text should return None."""
        result = calculate_metrics_from_text("", lang="ru")
        assert result is None

    def test_non_cyrillic_text_returns_none(self):
        """Non-cyrillic text should return None."""
        result = calculate_metrics_from_text("Hello world this is English text", lang="ru")
        assert result is None

    def test_uk_language_works(self):
        """Should work with Ukrainian text."""
        text = "Активна піна для безконтактної мийки автомобіля видаляє бруд"
        result = calculate_metrics_from_text(text, lang="uk")

        assert result is not None
        assert result["total_words"] > 0

    def test_uk_forms_share_one_lemma(self):
        """UK forms піна/піну/піною must be lemmatized by Ukrainian morphology."""
        text = "Активна піна для мийки. Наносимо піну на кузов. Кузов покритий піною."
        result = calculate_metrics_from_text(text, lang="uk")

        assert result is not None
        assert result["most_common_lemma"] == "піна"
        assert result["max_frequency"] == 3


class TestWaterCalculation:
    """Tests for water percentage calculation."""

    def test_high_stopword_text_has_high_water(self):
        """Text with many stopwords should have high water percent."""
        # Text with many stopwords
        text = "Это и есть то что нужно для того чтобы было хорошо и правильно"
        result = calculate_metrics_from_text(text, lang="ru")

        assert result is not None
        # Should have relatively high water due to stopwords
        assert result["water_count"] > 0


class TestNauseaCalculation:
    """Tests for nausea calculation."""

    def test_repeated_word_increases_nausea(self):
        """Repeated word should increase classic nausea."""
        # Normal text
        text1 = "Активная пена для мойки автомобиля удаляет грязь эффективно"
        result1 = calculate_metrics_from_text(text1, lang="ru")

        # Text with repeated word
        text2 = "Пена пена пена пена пена пена пена пена пена для мойки"
        result2 = calculate_metrics_from_text(text2, lang="ru")

        assert result1 is not None
        assert result2 is not None
        assert result2["classic_nausea"] > result1["classic_nausea"]


class TestUkTokenisation:
    """UK text: whole apostrophe words, no RU-only natasha tools."""

    def test_uk_apostrophe_words_counted_whole(self):
        text = "П'ять пір’їн. М'ясо та сімʼя."
        result = calculate_metrics_from_text(text, lang="uk")

        assert result is not None
        assert result["total_words"] == 5
        assert result["most_common_lemma"] != "п"

    def test_uk_runs_no_natasha_segmenter_or_tag_morph(self, monkeypatch):
        from llm_keywords_pipeline.audit import water

        def no_doc(*args, **kwargs):
            raise AssertionError("natasha Doc used for uk")

        monkeypatch.setattr(water, "Doc", no_doc)
        result = calculate_metrics_from_text("Активна піна для мийки", lang="uk")

        assert result is not None
        assert result["total_words"] == 4


def test_ru_metrics_unchanged():
    """RU result pinned to the value main produced before the UK tokenisation change."""
    text = (
        "Активная пена для бесконтактной мойки автомобиля. Пена эффективно удаляет грязь, "
        "а густая пена держится на кузове. Это и есть то, что нужно для мойки."
    )
    result = calculate_metrics_from_text(text, lang="ru")

    assert result is not None
    assert {k: result[k] for k in ("total_words", "water_count", "most_common_lemma")} == {
        "total_words": 24,
        "water_count": 10,
        "most_common_lemma": "пена",
    }
    assert result["max_frequency"] == 3
    assert result["total_significant"] == 5
    assert result["repeated_words_count"] == 7
    assert result["unique_lemmas"] == 20


def _fake_metrics(water_percent):
    return {
        "total_words": 100,
        "unique_lemmas": 60,
        "water_percent": water_percent,
        "water_percent_raw": water_percent / 2.4,
        "water_count": 25,
        "classic_nausea": 2.0,
        "most_common_lemma": "пена",
        "max_frequency": 4,
        "academic_nausea": 8.0,
        "most_common_significant": "пена",
        "max_freq_significant": 4,
        "total_significant": 50,
        "lemma_repetition_index": 10.0,
        "repeated_words_count": 10,
    }


def test_check_water_default_range_comes_from_config(monkeypatch, capsys):
    """Default water target is config 40-65: 62% passes, not a WARNING."""
    from llm_keywords_pipeline.audit import water

    monkeypatch.setattr(water, "calculate_metrics", lambda *a, **k: _fake_metrics(62.0))

    assert water.check_water("x.md") == 0
    out = capsys.readouterr().out
    assert "Цель: 40-65%" in out
    assert "Превышение на" not in out


def test_check_water_above_config_max_warns(monkeypatch, capsys):
    from llm_keywords_pipeline.audit import water

    monkeypatch.setattr(water, "calculate_metrics", lambda *a, **k: _fake_metrics(66.0))

    assert water.check_water("x.md") == 0
    assert "Превышение на 1.0%" in capsys.readouterr().out


def test_check_water_excess_single_warning_without_tier(monkeypatch, capsys):
    """Water above target_max: one WARNING message, no Tier wording (tiers are gone)."""
    from llm_keywords_pipeline.audit import water

    monkeypatch.setattr(water, "calculate_metrics", lambda *a, **k: _fake_metrics(68.0))

    assert water.check_water("x.md") == 0
    out = capsys.readouterr().out
    assert "   ⚠️ WARNING: Превышение на 3.0%\n" in out
    assert "Tier" not in out


def test_cli_accepts_float_water_bounds(monkeypatch, tmp_path):
    from llm_keywords_pipeline.audit import water

    md = tmp_path / "a.md"
    md.write_text("текст", encoding="utf-8")
    seen = {}
    monkeypatch.setattr(
        water, "check_water", lambda p, lo, hi, lang: seen.update(lo=lo, hi=hi) or 0
    )

    assert water.main([str(md), "40", "62.5"]) == 0
    assert seen == {"lo": 40.0, "hi": 62.5}
