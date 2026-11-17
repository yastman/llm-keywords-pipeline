"""Per-project config <data root>/project.toml (core.project) and the structure CSV path from it."""

import json
import os
import subprocess
import sys

import pytest

from llm_keywords_pipeline.core.project import (
    ProjectConfig,
    ProjectConfigError,
    load_project,
)

SEMANTICS_MODULES = [
    "llm_keywords_pipeline.core.config",
    "llm_keywords_pipeline.analyze.category",
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


def test_meta_required_phrases_per_language(tmp_path):
    (tmp_path / "project.toml").write_text(
        '[meta]\nrequired_phrases = { uk = ["опт\\\\b", "дистриб"], ru = [] }\n',
        encoding="utf-8",
    )

    project = load_project(tmp_path)

    assert project.required_phrases == {"uk": ("опт\\b", "дистриб"), "ru": ()}


def test_opencart_section(tmp_path):
    (tmp_path / "project.toml").write_text(
        '[opencart]\ntable_prefix = "oc_"\nlanguage_ids = { uk = 1, ru = 3 }\n', encoding="utf-8"
    )

    project = load_project(tmp_path)

    assert (project.opencart_table_prefix, project.opencart_language_ids) == (
        "oc_",
        {"uk": 1, "ru": 3},
    )
    assert load_project(tmp_path / "none").opencart_table_prefix is None


def test_no_meta_section_requires_no_phrase(tmp_path):
    (tmp_path / "project.toml").write_text('[project]\nbrand = "X"\n', encoding="utf-8")

    assert load_project(tmp_path).required_phrases == {}


@pytest.mark.parametrize(
    "body",
    [
        "[project]\nbrand = 1\n",
        "[project]\nsite = []\n",
        '[project]\nlanguages = "uk"\n',
        "[project]\nlanguages = [1]\n",
        "[paths]\nsemantics_csv = 5\n",
        "project = 1\n",
        'meta = "x"\n',
        '[meta]\nrequired_phrases = ["опт"]\n',
        '[meta]\nrequired_phrases = { uk = "опт" }\n',
        "[meta]\nrequired_phrases = { uk = [1] }\n",
        '[meta]\nrequired_phrases = { uk = ["(опт"] }\n',
        'opencart = "oc_"\n',
        "[opencart]\ntable_prefix = 5\n",
        "[opencart]\nlanguage_ids = [1, 3]\n",
        '[opencart]\nlanguage_ids = { uk = "1" }\n',
        "[opencart]\nlanguage_ids = { uk = true }\n",
    ],
)
def test_wrong_type_names_the_file(tmp_path, body):
    path = tmp_path / "project.toml"
    path.write_text(body, encoding="utf-8")

    with pytest.raises(ProjectConfigError, match=str(path)):
        load_project(tmp_path)


def test_non_utf8_file_names_the_file(tmp_path):
    path = tmp_path / "project.toml"
    path.write_bytes('[project]\nbrand = "Бренд"\n'.encode("cp1251"))

    with pytest.raises(ProjectConfigError, match=str(path)):
        load_project(tmp_path)


def test_load_is_cached_per_root(tmp_path):
    assert load_project(tmp_path) is load_project(tmp_path)


def test_unset_semantics_csv_is_none(tmp_path):
    # Empty data root: the repo's own files never decide the result.
    code = (
        "import importlib, json, sys\n"
        "print(json.dumps([importlib.import_module(m).SEMANTICS_CSV for m in sys.argv[1:]]))\n"
    )
    env = {**os.environ, "LLM_KEYWORDS_PROJECT_ROOT": str(tmp_path)}

    out = subprocess.run(
        [sys.executable, "-c", code, *SEMANTICS_MODULES],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert json.loads(out) == [None] * len(SEMANTICS_MODULES)


def test_command_needing_semantics_csv_stops_naming_the_key(tmp_path):
    env = {**os.environ, "LLM_KEYWORDS_PROJECT_ROOT": str(tmp_path)}

    result = subprocess.run(
        [sys.executable, "-m", "llm_keywords_pipeline.batch.generate", "--list"],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    # last line: runpy may warn first that batch/__init__ imported the module
    assert result.stderr.strip().splitlines()[-1] == (
        f"{tmp_path.resolve() / 'project.toml'}: [paths] semantics_csv is not set; "
        "this command needs it"
    )


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
