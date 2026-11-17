"""validate/content.py markdown lint: real pymarkdownlnt run, and a skipped lint is not silent."""

import pytest

from llm_keywords_pipeline.validate import content

_CLEAN_DOC = "# Активная пена\n\nАктивная пена для мойки.\n"


def test_mdlint_reports_known_violation(tmp_path) -> None:
    md = tmp_path / "doc.md"
    md.write_text("# Title\ntext with trailing spaces   \n", encoding="utf-8")

    result = content.check_markdown_lint(str(md))

    assert result["overall"] != "SKIPPED"
    assert {"MD022", "MD009"} <= {v["rule"] for v in result["violations"]}


def test_mdlint_unavailable_hint_names_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(content, "MDLINT_AVAILABLE", False)

    result = content.check_markdown_lint("missing.md")

    assert result["overall"] == "SKIPPED"
    assert "uv add pymarkdownlnt" in result["note"]


@pytest.mark.parametrize(("available", "expected"), [(False, True), (True, False)])
def test_skipped_mdlint_appears_in_summary_warnings(
    monkeypatch: pytest.MonkeyPatch, tmp_path, available: bool, expected: bool
) -> None:
    monkeypatch.setattr(content, "MDLINT_AVAILABLE", available)
    md = tmp_path / "doc.md"
    md.write_text(_CLEAN_DOC, encoding="utf-8")

    result = content.validate_content(str(md), "активная пена", use_semantic=False)

    assert result["checks"]["md_lint"]["overall"] == ("PASS" if available else "SKIPPED")
    assert ("md_lint: skipped" in result["summary"]["warnings"]) is expected
    assert "grammar" not in result["checks"]
