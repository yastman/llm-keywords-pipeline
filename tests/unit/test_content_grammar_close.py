"""check_grammar closes the LanguageTool instance on every path."""

from types import SimpleNamespace

import pytest

from llm_keywords_pipeline.validate import content

_MATCH = SimpleNamespace(message="m", context="ctx", ruleId="R", replacements=["a"])


def _install_stub(monkeypatch: pytest.MonkeyPatch, check) -> list[int]:
    closed: list[int] = []

    class _StubTool:
        def __init__(self, language: str) -> None:
            pass

        def check(self, text: str) -> list:
            return check()

        def close(self) -> None:
            closed.append(1)

    monkeypatch.setattr(content, "language_tool_python", SimpleNamespace(LanguageTool=_StubTool))
    monkeypatch.setattr(content, "GRAMMAR_AVAILABLE", True)
    return closed


def _raise() -> list:
    raise RuntimeError("boom")


@pytest.mark.parametrize(
    ("check", "overall"),
    [
        (lambda: [], "PASS"),
        (lambda: [_MATCH], "PASS"),
        (_raise, "ERROR"),
    ],
    ids=["no-matches", "matches", "exception"],
)
def test_check_grammar_closes_tool(monkeypatch: pytest.MonkeyPatch, check, overall: str) -> None:
    closed = _install_stub(monkeypatch, check)

    result = content.check_grammar("Текст.")

    assert result["overall"] == overall
    assert closed == [1]


def test_mdlint_unavailable_hint_names_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(content, "MDLINT_AVAILABLE", False)

    result = content.check_markdown_lint("missing.md")

    assert result["overall"] == "SKIPPED"
    assert "uv add pymarkdownlnt" in result["note"]
