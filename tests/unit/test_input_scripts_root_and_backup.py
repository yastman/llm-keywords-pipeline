"""Input scripts: project root from core.config (audit A11), timestamped CSV backups (A14)."""

import json
import os
import subprocess
import sys
from pathlib import Path

from llm_keywords_pipeline.core import config

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_MODULES = [
    "llm_keywords_pipeline.fix.missing_keywords:PROJECT_ROOT",
    "llm_keywords_pipeline.fix.structure_legacy:PROJECT_ROOT",
    "llm_keywords_pipeline.fix.structure_orphans:PROJECT_ROOT",
    "llm_keywords_pipeline.sync.migrate_keywords:BASE_DIR",
]
PROBE = (
    "import importlib, sys\n"
    "from llm_keywords_pipeline.core import config\n"
    "print(config.PROJECT_ROOT)\n"
    "for spec in sys.argv[1:]:\n"
    "    name, attr = spec.split(':')\n"
    "    print(getattr(importlib.import_module(name), attr))\n"
)


def _run(
    code: str, args: list[str], cwd: Path, env_root: str | None, check: bool = True
) -> list[str]:
    env = {k: v for k, v in os.environ.items() if k != "LLM_KEYWORDS_PROJECT_ROOT"}
    if env_root is not None:
        env["LLM_KEYWORDS_PROJECT_ROOT"] = env_root
    result = subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=check,
    )
    return result.stdout.splitlines()


def _roots(cwd: Path, env_root: str | None) -> list[str]:
    return _run(PROBE, ROOT_MODULES, cwd, env_root)


def test_ru_keywords_mapping_reads_and_writes_under_env_root(tmp_path):
    root = tmp_path / "root"
    data_dir = root / "categories" / "cat" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "cat_clean.json").write_text(
        json.dumps({"id": "cat", "keywords": [{"keyword": "k", "volume": 1}]}), encoding="utf-8"
    )
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()

    code = "from llm_keywords_pipeline.extract import ru_keywords_mapping as m; m.main()"
    _run(code, [], cwd, str(root), check=False)

    out = root / "data" / "generated" / "ru_keywords_mapping.json"
    assert out.is_file()
    assert list(json.loads(out.read_text(encoding="utf-8"))) == ["cat"]


def test_update_uk_clean_reads_and_writes_under_env_root(tmp_path):
    root = tmp_path / "root"
    (root / "uk" / "data").mkdir(parents=True)
    source = {
        "categories": {"cat": {"keywords": [{"keyword": "k", "volume": 600}], "total_volume": 600}}
    }
    (root / "uk" / "data" / "uk_keywords.json").write_text(json.dumps(source), encoding="utf-8")
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()

    code = "from llm_keywords_pipeline.sync import update_uk_clean as m; m.main()"
    _run(code, [], cwd, str(root), check=False)

    clean = root / "uk" / "categories" / "cat" / "data" / "cat_clean.json"
    assert clean.is_file()
    assert json.loads(clean.read_text(encoding="utf-8"))["total_volume"] == 600


def test_scripts_default_root_is_config_root_not_cwd(tmp_path):
    roots = _roots(tmp_path, None)
    assert roots == [str(REPO_ROOT)] * (1 + len(ROOT_MODULES))


def test_config_and_scripts_honour_env_root(tmp_path):
    env_root = tmp_path / "data-root"
    env_root.mkdir()
    roots = _roots(REPO_ROOT, str(env_root))
    assert roots == [str(env_root)] * (1 + len(ROOT_MODULES))


def test_match_cats_reads_dump_under_config_root(tmp_path, monkeypatch, capsys):
    from llm_keywords_pipeline.compare import match_cats

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_KEYWORDS_PROJECT_ROOT", raising=False)
    monkeypatch.setattr(Path, "exists", lambda self: False)
    match_cats.main()
    assert capsys.readouterr().out == (
        f"Dump not found: {config.PROJECT_ROOT / 'sql_cats_dump.txt'}\n"
    )


def _backups(csv_file: Path) -> list[Path]:
    return sorted(csv_file.parent.glob(f"{csv_file.stem}_backup*{csv_file.suffix}"))


def test_migrate_keywords_keeps_every_backup(tmp_path, monkeypatch):
    from llm_keywords_pipeline.sync import migrate_keywords

    csv_file = tmp_path / "structure.csv"
    csv_file.write_text("L1: Cat,,\nkey,10,\n", encoding="utf-8")
    registry = tmp_path / "registry.md"
    registry.write_text("", encoding="utf-8")
    monkeypatch.setattr(migrate_keywords, "CSV_FILE", csv_file)
    monkeypatch.setattr(migrate_keywords, "REGISTRY_FILE", registry)

    migrate_keywords.migrate_keywords()
    migrate_keywords.migrate_keywords()

    assert len(_backups(csv_file)) == 2


def test_csv_structure_keeps_every_backup(tmp_path, monkeypatch):
    from llm_keywords_pipeline.fix import csv_structure

    csv_file = tmp_path / "structure.csv"
    monkeypatch.setattr(csv_structure, "SEMANTICS_CSV", csv_file)

    csv_file.write_text("key one,2,\n", encoding="utf-8")
    csv_structure.fix_csv()
    csv_file.write_text("key two,3,\n", encoding="utf-8")
    csv_structure.fix_csv()

    backups = _backups(csv_file)
    assert [b.read_text(encoding="utf-8") for b in backups] == ["key one,2,\n", "key two,3,\n"]
