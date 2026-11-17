"""Smoke test: llm-keywords-audit-water --help must print usage and exit 0."""

import pytest

from llm_keywords_pipeline.audit.water import main


def test_help_prints_usage_and_exits_0(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    assert "usage:" in capsys.readouterr().out
