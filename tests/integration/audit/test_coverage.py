"""Tests for audit/coverage.py"""

from llm_keywords_pipeline.audit.coverage import (
    find_category_path,
    get_all_slugs,
)


class TestFindCategoryPath:
    """Tests for find_category_path function."""

    def test_find_uk_category_returns_path_if_exists(self):
        """UK category path should be found if exists."""
        # This test will pass if any UK category exists
        slugs = get_all_slugs("uk")
        if slugs:
            path = find_category_path(slugs[0], "uk")
            assert path is not None
            assert path.exists()

    def test_find_nonexistent_category_returns_none(self):
        """Non-existent category should return None."""
        path = find_category_path("nonexistent-category-xyz", "uk")
        assert path is None


class TestGetAllSlugs:
    """Tests for get_all_slugs function."""

    def test_get_all_uk_slugs_returns_list(self):
        """Should return a list of slugs."""
        slugs = get_all_slugs("uk")
        assert isinstance(slugs, list)

    def test_get_all_ru_slugs_returns_list(self):
        """Should return a list of slugs."""
        slugs = get_all_slugs("ru")
        assert isinstance(slugs, list)
