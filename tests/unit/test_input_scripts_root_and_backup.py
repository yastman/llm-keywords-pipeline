"""Input scripts: project root from core.config (audit A11), timestamped CSV backups (A14)."""

import os
import subprocess
import sys
from pathlib import Path

from llm_keywords_pipeline.core import config

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_MODULES = [
    "llm_keywords_pipeline.fix.missing_keywords",
    "llm_keywords_pipeline.fix.structure_legacy",
    "llm_keywords_pipeline.fix.structure_orphans",
]
PROBE = (
    "import importlib, sys\n"
    "from llm_keywords_pipeline.core import config\n"
    "print(config.PROJECT_ROOT)\n"
    "for name in sys.argv[1:]:\n"
    "    print(importlib.import_module(name).PROJECT_ROOT)\n"
)


def _roots(cwd: Path, env_root: str | None) -> list[str]:
    env = {k: v for k, v in os.environ.items() if k != "LLM_KEYWORDS_PROJECT_ROOT"}
    if env_root is not None:
        env["LLM_KEYWORDS_PROJECT_ROOT"] = env_root
    result = subprocess.run(
        [sys.executable, "-c", PROBE, *ROOT_MODULES],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()


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
