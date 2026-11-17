"""Data-writing CLIs must reject unknown flags instead of silently dry-running."""

import pytest

from llm_keywords_pipeline.compare import raw_clean
from llm_keywords_pipeline.fix import cleanup_misplaced, find_orphan_keywords

PARSERS = [raw_clean.parse_args, find_orphan_keywords.parse_args, cleanup_misplaced.parse_args]


@pytest.mark.parametrize("parse_args", PARSERS)
def test_unknown_flag_exits_2(parse_args):
    with pytest.raises(SystemExit) as exc:
        parse_args(["--aply"])
    assert exc.value.code == 2


@pytest.mark.parametrize("parse_args", PARSERS)
def test_help_exits_0(parse_args):
    with pytest.raises(SystemExit) as exc:
        parse_args(["--help"])
    assert exc.value.code == 0


def test_raw_clean_flags():
    assert raw_clean.parse_args([]).fix is False
    assert raw_clean.parse_args([]).slug is None
    args = raw_clean.parse_args(["aktivnaya-pena", "--fix"])
    assert args.fix is True
    assert args.slug == "aktivnaya-pena"


def test_raw_clean_unknown_flag_value_not_taken_as_slug():
    with pytest.raises(SystemExit) as exc:
        raw_clean.parse_args(["--fx", "aktivnaya-pena"])
    assert exc.value.code == 2


def test_raw_clean_main_rejects_unknown_flag_before_reading(monkeypatch):
    def fail():
        raise AssertionError("CSV read before argument check")

    monkeypatch.setattr(raw_clean, "parse_csv_keywords", fail)
    with pytest.raises(SystemExit) as exc:
        raw_clean.main(["--aply"])
    assert exc.value.code == 2


def test_find_orphan_flags():
    args = find_orphan_keywords.parse_args([])
    assert (args.distribute, args.apply) == (False, False)
    args = find_orphan_keywords.parse_args(["--distribute", "--apply"])
    assert (args.distribute, args.apply) == (True, True)


def test_cleanup_misplaced_flags():
    assert cleanup_misplaced.parse_args([]).fix is False
    assert cleanup_misplaced.parse_args(["--fix"]).fix is True


def test_cleanup_misplaced_main_rejects_unknown_flag_before_reading(monkeypatch):
    def fail(_slug):
        raise AssertionError("category read before argument check")

    monkeypatch.setattr(cleanup_misplaced, "analyze_category", fail)
    with pytest.raises(SystemExit) as exc:
        cleanup_misplaced.main(["--aply"])
    assert exc.value.code == 2
