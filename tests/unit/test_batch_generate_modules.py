"""batch.generate calls the real analyze/validate modules; fix prompt keeps full content."""

import inspect
import json
import subprocess
import sys

from llm_keywords_pipeline.batch import generate


def _fake_run(calls, stdout):
    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    return run


def test_run_analyze_invokes_analyze_category_module(monkeypatch):
    calls = []
    monkeypatch.setattr(generate.subprocess, "run", _fake_run(calls, json.dumps({"ok": 1})))

    ok, data = generate.run_analyze("aksessuary")

    assert calls == [
        [sys.executable, "-m", "llm_keywords_pipeline.analyze.category", "aksessuary", "--json"]
    ]
    assert ok is True
    assert data == {"ok": 1}


def test_run_analyze_error_falls_back_to_stdout(monkeypatch):
    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="Category not found: x\n", stderr="")

    monkeypatch.setattr(generate.subprocess, "run", run)

    assert generate.run_analyze("x") == (False, {"error": "Category not found: x\n"})


def test_run_analyze_error_prefers_stderr(monkeypatch):
    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, stdout="out", stderr="Traceback")

    monkeypatch.setattr(generate.subprocess, "run", run)

    assert generate.run_analyze("x") == (False, {"error": "Traceback"})


def test_run_validate_invokes_validate_content_module(monkeypatch, tmp_path):
    content_file = tmp_path / "aksessuary" / "content" / "aksessuary_ru.md"
    content_file.parent.mkdir(parents=True)
    content_file.write_text("# H1\n", encoding="utf-8")
    monkeypatch.setattr(generate, "CATEGORIES_DIR", tmp_path)
    calls = []
    stdout = json.dumps({"summary": {"overall": "PASS"}})
    monkeypatch.setattr(generate.subprocess, "run", _fake_run(calls, stdout))

    ok, data = generate.run_validate("aksessuary", "аксессуары")

    assert calls == [
        [
            sys.executable,
            "-m",
            "llm_keywords_pipeline.validate.content",
            str(content_file),
            "аксессуары",
            "--json",
        ]
    ]
    assert ok is True
    assert data["status"] == "PASS"


def test_fix_prompt_embeds_full_content():
    content = "A" * 4999 + "Z"

    prompt = generate.generate_fix_prompt("slug", ["h1_missing"], content)

    assert content in prompt


def test_resume_reruns_every_failed_slug(monkeypatch):
    log = {
        "categories": {
            "a": {"last_status": "FAIL"},
            "b": {"last_status": "PASS"},
            "c": {"last_status": "FAIL"},
        }
    }
    calls = []
    monkeypatch.setattr(generate, "load_batch_log", lambda: log)
    monkeypatch.setattr(generate, "process_category", lambda slug, lg: calls.append(slug))
    monkeypatch.setattr(sys, "argv", ["generate", "--resume"])

    generate.main()

    assert calls == ["a", "c"]


def test_failed_validation_writes_fix_prompt_without_self_heal_claim(monkeypatch, tmp_path, capsys):
    content_dir = tmp_path / "s" / "content"
    content_dir.mkdir(parents=True)
    (content_dir / "s_ru.md").write_text("# H1\n", encoding="utf-8")
    monkeypatch.setattr(generate, "CATEGORIES_DIR", tmp_path)
    monkeypatch.setattr(generate, "save_batch_log", lambda log: None)
    monkeypatch.setattr(generate, "run_analyze", lambda slug: (True, {"keywords": {}}))
    validation = {"status": "FAIL", "output": "H1 missing"}
    monkeypatch.setattr(generate, "run_validate", lambda slug, kw: (True, validation))
    monkeypatch.setattr(generate, "extract_issues_from_validation", lambda v: ["h1_missing"])
    log = {"categories": {}}

    assert generate.process_category("s", log) is False

    assert (content_dir / "s_fix_prompt.md").exists()
    assert log["categories"]["s"]["last_status"] == "FAIL"
    assert "heal" not in capsys.readouterr().out.lower()


def test_process_category_has_no_fix_prompt_switch():
    assert "fix_prompt" not in inspect.signature(generate.process_category).parameters
