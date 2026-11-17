"""Regression tests for audit B26 (atomic state write) and B27 (slug fallback, dates)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from llm_keywords_pipeline.analyze import duplicates
from llm_keywords_pipeline.automation.orchestrator import CategoryRunState, _save_state
from llm_keywords_pipeline.generate import checklists
from llm_keywords_pipeline.generate.semantic_review import collect_keywords


class _FakeDate(date):
    @classmethod
    def today(cls) -> _FakeDate:
        return cls(2031, 4, 5)


def test_save_state_keeps_target_whole_when_write_fails(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    state_path.write_text('{"slug": "old"}', encoding="utf-8")

    def broken_write(self: Path, data: str, encoding: str | None = None) -> int:
        with self.open("w", encoding=encoding) as f:
            f.write(data[: len(data) // 2])
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", broken_write)
    with pytest.raises(OSError):
        _save_state(CategoryRunState(slug="new"), state_path)

    assert state_path.read_text(encoding="utf-8") == '{"slug": "old"}'


def test_save_state_writes_full_state(tmp_path):
    state_path = tmp_path / "state.json"
    _save_state(CategoryRunState(slug="new"), state_path)
    assert json.loads(state_path.read_text(encoding="utf-8"))["slug"] == "new"


def test_semantic_review_slug_falls_back_to_file_name(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "with-id_clean.json").write_text(
        json.dumps({"id": "with-id", "keywords": []}), encoding="utf-8"
    )
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "no-id_clean.json").write_text(
        json.dumps({"keywords": [{"keyword": "k", "volume": 1}]}), encoding="utf-8"
    )

    data = collect_keywords(tmp_path)

    assert [c["slug"] for c in data] == ["no-id", "with-id"]
    assert data[0]["name"] == "no-id"


def test_checklists_use_current_date(tmp_path, monkeypatch):
    monkeypatch.setattr(checklists, "date", _FakeDate, raising=False)
    monkeypatch.setattr(checklists, "TASKS_DIR", tmp_path)
    monkeypatch.setattr(checklists, "PIPELINE_STATUS_FILE", tmp_path / "PIPELINE_STATUS.md")
    status = dict.fromkeys(
        ["init", "meta", "research", "content", "uk", "quality", "deploy"], False
    )
    node = {
        "slug": "cat",
        "name": "Cat",
        "volume": 10,
        "type": "leaf",
        "parent": "-",
        "keywords": [],
    }

    checklists.generate_task_file(node, status)
    checklists.update_pipeline_status([node], {"cat": status})

    assert "**Last Updated:** 2031-04-05" in (tmp_path / "cat.md").read_text(encoding="utf-8")
    assert "**Updated:** 2031-04-05" in (tmp_path / "PIPELINE_STATUS.md").read_text(
        encoding="utf-8"
    )


def test_duplicates_report_uses_current_date(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(duplicates, "date", _FakeDate, raising=False)
    monkeypatch.chdir(tmp_path)

    duplicates.main()

    assert "**Дата создания:** 2031-04-05" in capsys.readouterr().out
