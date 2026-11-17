"""Smoke test for the llm-keywords-density CLI entry point (audit C11)."""

import pytest

from llm_keywords_pipeline.validate.density import main


def test_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0
    assert "--lang" in capsys.readouterr().out
