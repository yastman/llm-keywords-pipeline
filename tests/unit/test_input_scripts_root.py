"""Input scripts: project root from core.config (audit A11)."""

import json
import os
import subprocess
import sys
from pathlib import Path

from llm_keywords_pipeline.core import config

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_MODULES = [
    "llm_keywords_pipeline.generate.all_meta:PROJECT_ROOT",
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
