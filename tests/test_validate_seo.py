#!/usr/bin/env python3
"""Tests for validate_seo.py UK language support."""

from llm_keywords_pipeline.validate.seo import detect_language


class TestDetectLanguage:
    """Tests for detect_language function."""

    def test_uk_categories_path(self):
        """UK path detected correctly."""
        assert detect_language("uk/categories/aktivnaya-pena/content/file.md") == "uk"

    def test_uk_path_with_backslash(self):
        """Windows-style UK path detected correctly."""
        assert detect_language("uk\\categories\\aktivnaya-pena\\content\\file.md") == "uk"

    def test_ru_categories_path(self):
        """RU path detected correctly."""
        assert detect_language("categories/aktivnaya-pena/content/file.md") == "ru"

    def test_absolute_uk_path(self):
        """Absolute UK path detected correctly."""
        assert detect_language("/workspace/project/uk/categories/test/file.md") == "uk"

    def test_default_to_ru(self):
        """Unknown path defaults to RU."""
        assert detect_language("some/random/path/file.md") == "ru"


class TestH2KeywordMatching:
    """Tests for H2 keyword detection with language support."""

    def test_uk_h2_with_exact_match(self):
        """UK H2 matches keyword via exact match."""
        from llm_keywords_pipeline.validate.seo import check_keywords_in_h2

        text = """# Title

## Як обрати активну піну для безконтактної мийки

Some text here.

## Активна піна: поради щодо вибору

More text.

## Яка піна краще для автомобіля

Third section.

## FAQ

Questions.
"""
        # H2 "Активна піна:" contains the full keyword phrase → exact match
        result = check_keywords_in_h2(text, "активна піна", lang="uk")
        assert result["with_keyword"] >= 1
        assert result["total_h2"] == 4

    def test_ru_h2_with_partial_keyword_match(self):
        """RU H2 matches when every keyword word's lemma is present (words in between allowed)."""
        from llm_keywords_pipeline.validate.seo import check_keywords_in_h2

        text = """# Title

## Как выбрать щетка для мойки авто

Some text.

## FAQ

Questions.
"""
        # Lemmas щетка/для/авто all occur in the H2, "мойки" between them is fine
        result = check_keywords_in_h2(text, "щетка для авто", lang="ru")
        assert result["with_keyword"] >= 1

    def test_ru_h2_inflected_full_keyword_counts(self):
        """RU H2 with every keyword lemma in inflected form counts."""
        from llm_keywords_pipeline.validate.seo import check_keywords_in_h2

        text = "# T\n\n## Как выбрать активную пену\n\n## Как выбрать пену\n"
        result = check_keywords_in_h2(text, "активная пена", lang="ru")
        assert result["h2_with_keyword"] == ["Как выбрать активную пену"]
        assert result["h2_without_keyword"] == ["Как выбрать пену"]

    def test_uk_h2_inflected_full_keyword_counts(self):
        """UK H2 with every keyword lemma in inflected form counts."""
        from llm_keywords_pipeline.validate.seo import check_keywords_in_h2

        text = "# T\n\n## Як обрати активну піну\n\n## Як обрати піну\n"
        result = check_keywords_in_h2(text, "активна піна", lang="uk")
        assert result["h2_with_keyword"] == ["Як обрати активну піну"]
        assert result["h2_without_keyword"] == ["Як обрати піну"]


class TestIntroKeywordMatching:
    """Intro check: inflected forms match, 150-char limit applies."""

    def test_ru_intro_inflected_keyword_passes(self):
        from llm_keywords_pipeline.validate.seo import check_keyword_in_intro

        text = "# Активная пена\n\nКупить активную пену для мойки авто.\n"
        assert check_keyword_in_intro(text, "активная пена")["passed"]

    def test_uk_intro_inflected_keyword_passes(self):
        from llm_keywords_pipeline.validate.seo import check_keyword_in_intro

        text = "# Активна піна\n\nКупити активну піну для миття авто.\n"
        assert check_keyword_in_intro(text, "активна піна", lang="uk")["passed"]

    def test_intro_without_keyword_fails(self):
        from llm_keywords_pipeline.validate.seo import check_keyword_in_intro

        text = "# Активная пена\n\nКупить пену для мойки авто.\n"
        assert not check_keyword_in_intro(text, "активная пена")["passed"]

    def test_keyword_after_150_chars_with_h1_fails(self):
        from llm_keywords_pipeline.validate.seo import check_keyword_in_intro

        intro = "Средство для мойки автомобиля. " * 16 + "Активная пена."
        assert intro.lower().index("активная пена") >= 150
        text = f"# Заголовок\n\n{intro}\n"
        assert not check_keyword_in_intro(text, "активная пена")["passed"]
