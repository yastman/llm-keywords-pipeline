"""Tests for generate_sql.py"""

from llm_keywords_pipeline.generate.sql import (
    escape_sql,
    md_to_html,
)


class TestEscapeSql:
    """Test SQL escaping."""

    def test_escapes_single_quotes(self):
        """Single quotes should be escaped."""
        assert escape_sql("it's") == "it\\'s"

    def test_escapes_double_quotes(self):
        """Double quotes should be escaped."""
        assert escape_sql('say "hello"') == 'say \\"hello\\"'

    def test_escapes_backslashes(self):
        """Backslashes should be escaped."""
        assert escape_sql("path\\to") == "path\\\\to"

    def test_handles_empty_string(self):
        """Empty string should return empty."""
        assert escape_sql("") == ""

    def test_handles_cyrillic(self):
        """Cyrillic should be preserved."""
        assert escape_sql("Привет") == "Привет"

    def test_complex_escaping(self):
        """Multiple special chars in one string."""
        result = escape_sql('It\'s a "test" with \\ backslash')
        assert "\\'" in result
        assert '\\"' in result
        assert "\\\\" in result


class TestMdToHtmlGenerateSql:
    """Test md_to_html from generate_sql module."""

    def test_extracts_h1(self):
        """H1 should be extracted separately."""
        md = "# Заголовок\n\nТекст"
        h1, html = md_to_html(md)
        assert h1 == "Заголовок"
        assert "<h1>" not in html

    def test_returns_empty_h1_if_missing(self):
        """No H1 should return empty string."""
        md = "## H2 Only\n\nТекст"
        h1, html = md_to_html(md)
        assert h1 == ""

    def test_converts_body_to_html(self):
        """Body should be converted to HTML."""
        md = "# H1\n\n## H2\n\nПараграф"
        h1, html = md_to_html(md)
        assert "<h2>" in html or "H2" in html


class TestGenerateUpdateSqlMeta:
    """generate_update_sql must not blank store meta when meta is missing/empty."""

    def _setup(self, tmp_path, monkeypatch, meta_json=None):
        import llm_keywords_pipeline.generate.sql as sql_mod

        monkeypatch.setattr(sql_mod, "PROJECT_DIR", tmp_path)
        cat = tmp_path / "categories" / "slug"
        (cat / "content").mkdir(parents=True)
        (cat / "content" / "slug_ru.md").write_text("# H1\n\nText", encoding="utf-8")
        if meta_json is not None:
            (cat / "meta").mkdir()
            (cat / "meta" / "slug_meta.json").write_text(meta_json, encoding="utf-8")
        return sql_mod.generate_update_sql("slug", 7)

    def test_no_meta_file_omits_meta_fields(self, tmp_path, monkeypatch):
        out = self._setup(tmp_path, monkeypatch)
        assert "meta_title" not in out
        assert "meta_description" not in out
        assert "`description` = " in out
        assert "`meta_h1` = 'H1'" in out

    def test_empty_meta_values_omit_meta_fields(self, tmp_path, monkeypatch):
        out = self._setup(tmp_path, monkeypatch, '{"meta": {"title": "", "description": ""}}')
        assert "meta_title" not in out
        assert "meta_description" not in out

    def test_non_object_meta_omits_meta_fields(self, tmp_path, monkeypatch):
        out = self._setup(tmp_path, monkeypatch, "[]")
        assert "meta_title" not in out
        assert "meta_description" not in out

    def test_only_title_present(self, tmp_path, monkeypatch):
        out = self._setup(tmp_path, monkeypatch, '{"meta": {"title": "T"}}')
        assert "`meta_title` = 'T'," in out
        assert "meta_description" not in out

    def test_nested_meta_shape(self, tmp_path, monkeypatch):
        out = self._setup(tmp_path, monkeypatch, '{"meta": {"title": "T", "description": "D"}}')
        assert "`meta_title` = 'T'," in out
        assert "`meta_description` = 'D'," in out

    def test_top_level_meta_shape(self, tmp_path, monkeypatch):
        out = self._setup(tmp_path, monkeypatch, '{"title": "T", "description": "D", "h1": "H"}')
        assert "`meta_title` = 'T'," in out
        assert "`meta_description` = 'D'," in out
