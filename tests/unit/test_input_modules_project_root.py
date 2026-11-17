"""Input, sync, fix, extract and validate modules resolve paths via core.config (audit A1, C18)."""

import importlib
from pathlib import Path

import pytest

from llm_keywords_pipeline.core import config

ROOT_ATTRS = [
    ("llm_keywords_pipeline.sync.merge_master", "ROOT"),
    ("llm_keywords_pipeline.sync.semantics", "ROOT"),
    ("llm_keywords_pipeline.sync.update_volume", "ROOT"),
    ("llm_keywords_pipeline.sync.restore_csv", "PROJECT_ROOT"),
    ("llm_keywords_pipeline.compare.raw_clean", "PROJECT_ROOT"),
    ("llm_keywords_pipeline.compare.with_master", "ROOT"),
    ("llm_keywords_pipeline.fix.find_orphan_keywords", "PROJECT_ROOT"),
    ("llm_keywords_pipeline.fix.find_duplicates", "ROOT_DIR"),
    ("llm_keywords_pipeline.fix.keywords_order", "ROOT"),
    ("llm_keywords_pipeline.extract.all_keywords", "ROOT"),
    ("llm_keywords_pipeline.extract.ru_keywords_list", "ROOT"),
    ("llm_keywords_pipeline.extract.export_uk_texts", "ROOT"),
    ("llm_keywords_pipeline.core.synonyms", "PROJECT_ROOT"),
    ("llm_keywords_pipeline.validate.master", "ROOT"),
]

CATEGORIES_MODULES = [name for name, _ in ROOT_ATTRS if name.split(".")[-1] != "with_master"] + [
    "llm_keywords_pipeline.fix.cleanup_misplaced",
    "llm_keywords_pipeline.validate.structural",
]
CATEGORIES_MODULES.remove("llm_keywords_pipeline.extract.export_uk_texts")


@pytest.mark.parametrize(("module_name", "attr"), ROOT_ATTRS)
def test_module_root_is_project_root(module_name, attr):
    module = importlib.import_module(module_name)
    root = getattr(module, attr)
    assert root == config.PROJECT_ROOT
    assert (root / "pyproject.toml").is_file()


@pytest.mark.parametrize("module_name", CATEGORIES_MODULES)
def test_module_categories_dir_is_config_value(module_name):
    module = importlib.import_module(module_name)
    assert module.CATEGORIES_DIR == config.CATEGORIES_DIR


@pytest.mark.parametrize(
    ("module_name", "attr"),
    [
        ("llm_keywords_pipeline.sync.merge_master", "DEFAULT_OUTPUT"),
        ("llm_keywords_pipeline.sync.semantics", "DEFAULT_CSV"),
        ("llm_keywords_pipeline.validate.master", "DEFAULT_CSV"),
    ],
)
def test_master_csv_is_under_config_data_dir(module_name, attr):
    module = importlib.import_module(module_name)
    assert getattr(module, attr) == config.DATA_DIR / "ru_semantics_master.csv"


class _Stop(Exception):
    pass


def test_uk_keywords_reads_categories_under_project_root(monkeypatch):
    from llm_keywords_pipeline.extract import uk_keywords

    globbed: list[Path] = []

    def fake_glob(self, pattern):
        globbed.append(self)
        raise _Stop

    monkeypatch.setattr(Path, "glob", fake_glob)
    with pytest.raises(_Stop):
        uk_keywords.main()

    assert globbed == [config.CATEGORIES_DIR]


def test_uk_keywords_writes_under_project_data_dir(monkeypatch):
    from llm_keywords_pipeline.extract import uk_keywords

    made: list[Path] = []

    def fake_mkdir(self, *args, **kwargs):
        made.append(self)
        raise _Stop

    monkeypatch.setattr(Path, "glob", lambda self, pattern: iter(()))
    monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    with pytest.raises(_Stop):
        uk_keywords.main()

    assert made == [config.DATA_DIR / "generated"]


def test_uk_keywords_list_uses_project_root(monkeypatch):
    from llm_keywords_pipeline.extract import uk_keywords_list

    made: list[Path] = []

    def fake_mkdir(self, *args, **kwargs):
        made.append(self)
        raise _Stop

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    with pytest.raises(_Stop):
        uk_keywords_list.main()

    assert made == [config.DATA_DIR / "generated"]
