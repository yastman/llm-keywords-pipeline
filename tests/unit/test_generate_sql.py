"""Tests for generate_sql.py"""

import pytest

from llm_keywords_pipeline.generate.sql import (
    escape_sql,
    md_to_html,
)

OPENCART = '[opencart]\ntable_prefix = "oc_"\nlanguage_ids = { ru = 3 }\n'


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
        (tmp_path / "project.toml").write_text(OPENCART, encoding="utf-8")
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


class TestGenerateUpdateSqlOpencart:
    """Table and language id come from [opencart] of project.toml, no default."""

    def _sql(self, tmp_path, monkeypatch, project_toml):
        import llm_keywords_pipeline.generate.sql as sql_mod

        monkeypatch.setattr(sql_mod, "PROJECT_DIR", tmp_path)
        content = tmp_path / "categories" / "slug" / "content"
        content.mkdir(parents=True)
        (content / "slug_ru.md").write_text("# H1\n\nText", encoding="utf-8")
        (tmp_path / "project.toml").write_text(project_toml, encoding="utf-8")
        return sql_mod.generate_update_sql("slug", 7)

    def test_prefix_and_ru_language_id_from_config(self, tmp_path, monkeypatch):
        out = self._sql(
            tmp_path,
            monkeypatch,
            '[opencart]\ntable_prefix = "shop_"\nlanguage_ids = { uk = 1, ru = 4 }\n',
        )
        assert "UPDATE `shop_category_description`" in out
        assert "WHERE `category_id` = 7 AND `language_id` = 4;" in out

    @pytest.mark.parametrize(
        ("project_toml", "key"),
        [
            ("", "[opencart] table_prefix"),
            ("[opencart]\nlanguage_ids = { ru = 3 }\n", "[opencart] table_prefix"),
            ('[opencart]\ntable_prefix = "oc_"\nlanguage_ids = { uk = 1 }\n', "language_ids.ru"),
        ],
    )
    def test_missing_key_stops_naming_it(self, tmp_path, monkeypatch, project_toml, key):
        with pytest.raises(SystemExit) as exc:
            self._sql(tmp_path, monkeypatch, project_toml)
        assert key in str(exc.value)
        assert "project.toml" in str(exc.value)


@pytest.mark.parametrize(
    ("project_toml", "key"),
    [
        (None, "[opencart] table_prefix"),
        ("[opencart]\nlanguage_ids = { ru = 3 }\n", "[opencart] table_prefix"),
        ('[opencart]\ntable_prefix = "oc_"\nlanguage_ids = { uk = 1 }\n', "language_ids.ru"),
    ],
)
def test_cli_without_opencart_key_stops_before_writing(tmp_path, project_toml, key):
    """The shipped empty CATEGORY_MAP still checks [opencart] and writes no file."""
    import os
    import subprocess
    import sys

    if project_toml is not None:
        (tmp_path / "project.toml").write_text(project_toml, encoding="utf-8")
    env = {**os.environ, "LLM_KEYWORDS_PROJECT_ROOT": str(tmp_path)}

    result = subprocess.run(
        [sys.executable, "-m", "llm_keywords_pipeline.generate.sql"],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert key in result.stderr
    assert not (tmp_path / "content_updates.sql").exists()
