"""Per-project config <data root>/project.toml (core.project) and the structure CSV path from it."""

import importlib
import json
import os
import subprocess
import sys

import pytest

from llm_keywords_pipeline.core import config
from llm_keywords_pipeline.core.project import (
    ProjectConfig,
    ProjectConfigError,
    get_project,
    load_project,
)

SEMANTICS_MODULES = [
    "llm_keywords_pipeline.core.config",
    "llm_keywords_pipeline.analyze.category",
    "llm_keywords_pipeline.fix.find_orphan_keywords",
    "llm_keywords_pipeline.sync.restore_csv",
    "llm_keywords_pipeline.compare.raw_clean",
    "llm_keywords_pipeline.batch.generate",
    "llm_keywords_pipeline.extract.export_uk_texts",
]


def test_missing_file_is_empty_config(tmp_path):
    assert load_project(tmp_path) == ProjectConfig()
    assert load_project(tmp_path).semantics_csv is None


def test_partial_file_fills_only_given_keys(tmp_path):
    (tmp_path / "project.toml").write_text(
        '[project]\nbrand = "Genesis"\n\n[paths]\nsemantics_csv = "data/s.csv"\n',
        encoding="utf-8",
    )

    project = load_project(tmp_path)

    assert project.brand == "Genesis"
    assert project.semantics_csv == "data/s.csv"
    assert project.site == ""
    assert project.languages == ()


def test_broken_file_names_the_file(tmp_path):
    path = tmp_path / "project.toml"
    path.write_text("[paths\nsemantics_csv = 1\n", encoding="utf-8")

    with pytest.raises(ProjectConfigError, match=str(path)):
        load_project(tmp_path)


def test_load_is_cached_per_root(tmp_path):
    assert load_project(tmp_path) is load_project(tmp_path)


@pytest.mark.parametrize(
    ("module_name", "legacy"),
    [
        ("llm_keywords_pipeline.core.config", "Структура _Ultimate.csv"),
        ("llm_keywords_pipeline.analyze.category", "Структура _Ultimate.csv"),
        ("llm_keywords_pipeline.fix.find_orphan_keywords", "Структура _Ultimate.csv"),
        ("llm_keywords_pipeline.sync.restore_csv", "Структура _Ultimate.csv"),
        ("llm_keywords_pipeline.compare.raw_clean", "Структура _Ultimate.csv"),
        ("llm_keywords_pipeline.batch.generate", "data/Структура  Ultimate финал - Лист2.csv"),
        (
            "llm_keywords_pipeline.extract.export_uk_texts",
            "data/Структура  Ultimate финал - Лист2.csv",
        ),
    ],
)
def test_unset_semantics_csv_keeps_old_name(module_name, legacy):
    assert get_project().semantics_csv is None
    module = importlib.import_module(module_name)
    assert module.SEMANTICS_CSV == config.PROJECT_ROOT / legacy


def test_every_module_reads_semantics_csv_from_project_toml(tmp_path):
    (tmp_path / "project.toml").write_text(
        '[paths]\nsemantics_csv = "data/Структура.csv"\n', encoding="utf-8"
    )
    code = (
        "import importlib, json, sys\n"
        "print(json.dumps([str(importlib.import_module(m).SEMANTICS_CSV) for m in sys.argv[1:]]))\n"
    )
    env = {**os.environ, "LLM_KEYWORDS_PROJECT_ROOT": str(tmp_path)}

    out = subprocess.run(
        [sys.executable, "-c", code, *SEMANTICS_MODULES],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    expected = str(tmp_path.resolve() / "data" / "Структура.csv")
    assert json.loads(out) == [expected] * len(SEMANTICS_MODULES)
