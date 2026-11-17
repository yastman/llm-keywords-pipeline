"""Smoke tests for fix package — issue #14 coverage."""


class TestFixPackageImports:
    """All fix submodules must be importable."""

    def test_fix_importable(self):
        import llm_keywords_pipeline.fix  # noqa: F401

    def test_keywords_order_importable(self):
        from llm_keywords_pipeline.fix import keywords_order  # noqa: F401

    def test_find_duplicates_importable(self):
        from llm_keywords_pipeline.fix import find_duplicates  # noqa: F401

    def test_cleanup_misplaced_importable(self):
        from llm_keywords_pipeline.fix import cleanup_misplaced  # noqa: F401


class TestFixCategoryKeywordsOrder:
    """fix.keywords_order.fix_category must return a dict."""

    def test_returns_dict_for_valid_data(self, tmp_path):
        import json

        from llm_keywords_pipeline.fix.keywords_order import fix_category

        data = {
            "slug": "test",
            "keywords": [
                {"keyword": "авто", "volume": 50},
                {"keyword": "машина", "volume": 100},
            ],
        }
        f = tmp_path / "test_clean.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        result = fix_category(f)
        assert isinstance(result, dict)
