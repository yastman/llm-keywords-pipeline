"""Smoke test for the llm-keywords-density CLI entry point (audit C11)."""

import json

import pytest

from llm_keywords_pipeline.validate import density
from llm_keywords_pipeline.validate.density import main


def test_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0
    assert "--lang" in capsys.readouterr().out


def test_cli_keyword_check_uses_lang(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(density, "load_keywords_from_json", lambda slug: ["активна піна"])
    md = tmp_path / "uk.md"
    md.write_text("Наносимо активну піну. Активну піну змивають.\n", encoding="utf-8")

    main([str(md), "--with-keywords", "x", "--lang", "uk", "--json"])

    keywords_check = json.loads(capsys.readouterr().out)["keywords_check"]
    assert keywords_check[0]["exact_count"] == 2
