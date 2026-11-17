"""Regression tests for automation defects (audit B9–B13)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
import requests

from llm_keywords_pipeline.automation.batch_runner import run_batch
from llm_keywords_pipeline.automation.llm_client import (
    HttpLlmClient,
    MockLlmClient,
    render_prompt_template,
)
from llm_keywords_pipeline.automation.orchestrator import run_category
from llm_keywords_pipeline.core.models import Category

OK_BODY = {"choices": [{"message": {"content": "ok"}}], "usage": {}}


def _resp(status: int, body: object = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = OK_BODY if body is None else body
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status}", response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr("llm_keywords_pipeline.automation.llm_client.time.sleep", lambda _s: None)
    return HttpLlmClient(endpoint="http://llm.invalid", model="m", max_retries=3)


# ── B9: retry only transient failures ───────────────────────────────────────


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_client_error_is_not_retried(client, status):
    with patch("requests.post", return_value=_resp(status)) as post, pytest.raises(Exception):
        client.complete("hi")
    assert post.call_count == 1


@pytest.mark.parametrize("body", [{}, {"choices": []}, {"choices": [{"message": {}}]}])
def test_paid_200_with_bad_shape_is_not_retried(client, body):
    with patch("requests.post", return_value=_resp(200, body)) as post, pytest.raises(Exception):
        client.complete("hi")
    assert post.call_count == 1


def test_200_with_invalid_json_is_not_retried(client):
    resp = _resp(200)
    resp.json.side_effect = requests.JSONDecodeError("bad", "doc", 0)
    with patch("requests.post", return_value=resp) as post, pytest.raises(Exception):
        client.complete("hi")
    assert post.call_count == 1


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_429_and_5xx_are_retried_until_success(client, status):
    with patch("requests.post", side_effect=[_resp(status), _resp(status), _resp(200)]) as post:
        assert client.complete("hi").text == "ok"
    assert post.call_count == 3


@pytest.mark.parametrize("exc", [requests.Timeout("t"), requests.ConnectionError("c")])
def test_timeout_and_connection_errors_are_retried(client, exc):
    with patch("requests.post", side_effect=exc) as post, pytest.raises(RuntimeError):
        client.complete("hi")
    assert post.call_count == 3


# ── B10: max_retries=0 ──────────────────────────────────────────────────────


def test_run_category_max_retries_zero_validates_once_without_revise(tmp_path):
    llm = MockLlmClient("no cyrillic content here at all")
    state = run_category(Category(slug="zero"), llm, state_dir=tmp_path, max_retries=0)
    assert state.state == "needs_human"
    assert state.last_stage("produce").attempts == 1
    assert len(llm.calls) == 1  # produce only, no revise


# ── B11: run_batch honours LLM_MAX_RETRIES ──────────────────────────────────


def test_run_batch_default_max_retries_follows_env():
    code = (
        "import inspect\n"
        "from llm_keywords_pipeline.automation import orchestrator\n"
        "from llm_keywords_pipeline.automation.batch_runner import run_batch\n"
        "print(inspect.signature(run_batch).parameters['max_retries'].default, orchestrator.MAX_RETRIES)\n"
    )
    env = {**os.environ, "LLM_MAX_RETRIES": "5"}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.split() == ["5", "5"]


# ── B12: needs_human.json always written ────────────────────────────────────


def test_needs_human_json_overwritten_with_empty_list(tmp_path):
    (tmp_path / "needs_human.json").write_text(json.dumps(["t1"]), encoding="utf-8")
    llm = MockLlmClient("# Заголовок\n\nТестовый текст для проверки водности.")
    report = run_batch([Category(slug="ok")], llm, state_dir=tmp_path)
    assert report.needs_human == 0
    assert json.loads((tmp_path / "needs_human.json").read_text(encoding="utf-8")) == []


# ── B13: {name} placeholders ────────────────────────────────────────────────


def test_render_prompt_template_braces(tmp_path):
    tmpl = tmp_path / "t.md"
    tmpl.write_text("slug: {slug}, tier: {tier}, other: {unknown}", encoding="utf-8")
    assert render_prompt_template(tmpl, {"slug": "abc", "tier": 2}) == "slug: abc, tier: 2, other: {unknown}"
