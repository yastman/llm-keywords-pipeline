"""Tests for validate_density.py UK support."""

from llm_keywords_pipeline.core.text import (
    STOPWORDS_RU,
    STOPWORDS_UK,
    get_stopwords,
    tokenize,
)
from llm_keywords_pipeline.validate.density import (
    STEMMER_RU,
    count_stem_frequencies,
)


class TestStopwords:
    """Tests for language-specific stopwords."""

    def test_get_stopwords_ru_default(self):
        """Default returns Russian stopwords."""
        result = get_stopwords()
        assert result is STOPWORDS_RU

    def test_get_stopwords_ru_explicit(self):
        """Explicit ru returns Russian stopwords."""
        result = get_stopwords("ru")
        assert result is STOPWORDS_RU

    def test_get_stopwords_uk(self):
        """uk returns Ukrainian stopwords."""
        result = get_stopwords("uk")
        assert result is STOPWORDS_UK

    def test_stopwords_ru_contains_common(self):
        """Russian stopwords contain common words."""
        assert "и" in STOPWORDS_RU
        assert "в" in STOPWORDS_RU
        assert "на" in STOPWORDS_RU
        assert "но" in STOPWORDS_RU

    def test_stopwords_uk_contains_common(self):
        """Ukrainian stopwords contain common words."""
        assert "і" in STOPWORDS_UK
        assert "в" in STOPWORDS_UK
        assert "на" in STOPWORDS_UK
        assert "але" in STOPWORDS_UK

    def test_stopwords_are_different(self):
        """RU and UK stopwords are different sets."""
        assert STOPWORDS_RU != STOPWORDS_UK
        # "но" is Russian, "але" is Ukrainian equivalent
        assert "но" in STOPWORDS_RU
        assert "но" not in STOPWORDS_UK
        assert "але" in STOPWORDS_UK
        assert "але" not in STOPWORDS_RU


class TestTokenizeStopwords:
    """Tests for tokenize with stopwords removal (via text_utils)."""

    def test_tokenize_removes_ru_stopwords(self):
        """Tokenize with remove_stopwords=True removes Russian stopwords."""
        text = "активная и пена для авто"
        result = tokenize(text, lang="ru", remove_stopwords=True)
        assert "и" not in result
        assert "для" not in result
        assert "активная" in result
        assert "пена" in result
        assert "авто" in result

    def test_tokenize_removes_uk_stopwords(self):
        """Tokenize with remove_stopwords=True removes Ukrainian stopwords."""
        text = "активна і піна для авто"
        result = tokenize(text, lang="uk", remove_stopwords=True)
        assert "і" not in result
        assert "для" not in result
        assert "активна" in result
        assert "піна" in result
        assert "авто" in result

    def test_tokenize_removes_short_words(self):
        """Tokenize removes words with len <= 2."""
        text = "авто в на шампунь"
        result = tokenize(text, lang="ru", remove_stopwords=True)
        assert "в" not in result
        assert "на" not in result
        assert "авто" in result
        assert "шампунь" in result


class TestStemmer:
    """Tests for language-specific word-form grouping."""

    def test_ru_stemmer(self):
        """RU groups by Snowball Russian stem."""
        assert STEMMER_RU.stemWord("полировальная") == "полировальн"

    def test_uk_groups_by_lemma(self):
        """UK groups by Ukrainian lemma, not by the Russian stemmer."""
        result = count_stem_frequencies(
            ["полірувальна", "полірувальну", "полірувальною"], lang="uk"
        )
        assert {k: v["count"] for k, v in result.items()} == {"полірувальний": 3}
