"""batch.uk_init.process_category: research path, project root, skip-existing (owner Q6)."""

import json
import os
import subprocess
import sys
from datetime import date

import pytest

from llm_keywords_pipeline.batch import uk_init
from llm_keywords_pipeline.batch.uk_init import process_category

SLUG = "aksessuary"
RU_META_PATH = "categories/aksessuary/meta/aksessuary_meta.json"
RU_META = {"h1": "Аксессуары", "meta": {"title": "Аксессуары", "description": "Аксессуары"}}
CREATED_KEYS = ("meta_created", "clean_created", "context_created")


def _write_ru_meta(root):
    ru_meta = root / RU_META_PATH
    ru_meta.parent.mkdir(parents=True)
    ru_meta.write_text(json.dumps(RU_META), encoding="utf-8")


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(uk_init, "PROJECT_ROOT", tmp_path)
    _write_ru_meta(tmp_path)
    return tmp_path


def _outputs(root):
    uk_dir = root / "uk" / "categories" / SLUG
    return [
        uk_dir / "meta" / f"{SLUG}_meta.json",
        uk_dir / "data" / f"{SLUG}_clean.json",
        uk_dir / "research" / "CONTEXT.md",
    ]


def test_context_points_to_category_research_data(root):
    result = process_category(SLUG, RU_META_PATH)

    context = (root / result["context_created"]).read_text(encoding="utf-8")
    assert "See: categories/aksessuary/research/RESEARCH_DATA.md" in context


def test_updated_at_is_today(root):
    result = process_category(SLUG, RU_META_PATH)

    meta = json.loads((root / result["meta_created"]).read_text(encoding="utf-8"))
    assert meta["updated_at"] == date.today().isoformat()


def test_existing_files_are_skipped_without_force(root):
    outputs = _outputs(root)
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("hand-edited", encoding="utf-8")

    result = process_category(SLUG, RU_META_PATH)

    assert [p.read_text(encoding="utf-8") for p in outputs] == ["hand-edited"] * 3
    assert result["skipped"] == [str(p) for p in outputs]
    assert [result[k] for k in CREATED_KEYS] == [None, None, None]


def test_existing_files_are_overwritten_with_force(root):
    outputs = _outputs(root)
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("hand-edited", encoding="utf-8")

    result = process_category(SLUG, RU_META_PATH, force=True)

    assert all(p.read_text(encoding="utf-8") != "hand-edited" for p in outputs)
    assert result["skipped"] == []
    assert [result[k] for k in CREATED_KEYS] == [str(p) for p in outputs]


def test_missing_files_are_written_without_force(root):
    result = process_category(SLUG, RU_META_PATH)

    assert all(p.exists() for p in _outputs(root))
    assert result["skipped"] == []
    assert [result[k] for k in CREATED_KEYS] == [str(p) for p in _outputs(root)]


def _run_main(cwd, env_root, *args):
    env = {k: v for k, v in os.environ.items() if k != "LLM_KEYWORDS_PROJECT_ROOT"}
    env["LLM_KEYWORDS_PROJECT_ROOT"] = str(env_root)
    return subprocess.run(
        [sys.executable, "-m", "llm_keywords_pipeline.batch.uk_init", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_main_uses_env_project_root_and_force_flag(tmp_path):
    root = tmp_path / "root"
    _write_ru_meta(root)
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    meta_path = _outputs(root)[0]

    _run_main(cwd, root)
    assert meta_path.exists()
    assert not (cwd / "uk").exists()

    meta_path.write_text("hand-edited", encoding="utf-8")
    out = _run_main(cwd, root)
    assert meta_path.read_text(encoding="utf-8") == "hand-edited"
    assert f"skipped {meta_path}" in out

    _run_main(cwd, root, "--force")
    assert meta_path.read_text(encoding="utf-8") != "hand-edited"
