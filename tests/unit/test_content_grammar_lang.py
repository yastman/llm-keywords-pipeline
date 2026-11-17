"""Grammar check in validate.content uses the file's language."""

import pytest

from llm_keywords_pipeline.validate import content


class _StubTool:
    def __init__(self, language: str, calls: list[str]) -> None:
        calls.append(language)

    def check(self, text: str) -> list:
        return []

    def close(self) -> None:
        pass


@pytest.fixture
def lt_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    class _StubModule:
        @staticmethod
        def LanguageTool(language: str) -> _StubTool:  # noqa: N802
            return _StubTool(language, calls)

    monkeypatch.setattr(content, "language_tool_python", _StubModule)
    monkeypatch.setattr(content, "GRAMMAR_AVAILABLE", True)
    return calls


@pytest.mark.parametrize(("lang", "expected"), [("uk", "uk-UA"), ("ru", "ru-RU")])
def test_check_grammar_uses_language_of_lang(lt_calls: list[str], lang: str, expected: str) -> None:
    result = content.check_grammar("Текст.", lang=lang)

    assert lt_calls == [expected]
    assert result["overall"] == "PASS"


@pytest.mark.parametrize(("lang", "expected"), [("uk", "uk-UA"), ("ru", "ru-RU")])
def test_validate_content_passes_lang_to_grammar(
    lt_calls: list[str], tmp_path, lang: str, expected: str
) -> None:
    md = tmp_path / "page.md"
    md.write_text("# Заголовок\n\nТекст про активну піну.\n", encoding="utf-8")

    content.validate_content(str(md), primary_keyword="піна", mode="quality", lang=lang)

    assert lt_calls == [expected]


def test_unavailable_hint_names_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(content, "GRAMMAR_AVAILABLE", False)

    result = content.check_grammar("Текст.")

    assert result["overall"] == "SKIPPED"
    assert "uv add language-tool-python" in result["note"]
