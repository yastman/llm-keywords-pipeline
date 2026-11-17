"""Smoke test: llm-keywords-check-seo --help prints usage and exits 0."""

from llm_keywords_pipeline.validate.seo import main


def test_help_exits_zero_and_names_command(capsys):
    assert main(["--help"]) == 0
    assert "llm-keywords-check-seo" in capsys.readouterr().out


def test_missing_args_exits_two(capsys):
    assert main([]) == 2
    assert "llm-keywords-check-seo" in capsys.readouterr().out
