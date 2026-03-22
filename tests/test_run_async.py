# -*- coding: utf-8 -*-
# Author: xiaoyao.zhao
# Designer: xiaoyao.zhao
# Coder: xiaoyao.zhao
# Email: 3199489460@qq.com
# License: paperagent
# Copyright (c) 2026 paperagent Authors. All rights reserved.


"""
Module Introduction
-------------------

This module implements minimal automated tests for run async/cancel behavior.
"""


from argparse import Namespace
from pathlib import Path

import pytest

from paper_agent.cli import _resolve_run_task_args, _spawn_async_worker
from paper_agent.config import AppConfig
from paper_agent.workflow.service import PaperAgentService


def _build_args(**kwargs) -> Namespace:
    defaults = {
        "task": "index",
        "query": None,
        "limit": 10,
        "top_k": 5,
        "author": None,
        "categories": [],
        "from_year": None,
        "to_year": None,
        "no_review": False,
        "no_cluster": False,
        "provider": "zotero",
        "library_path": "",
        "collection_id": None,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


def test_resolve_run_task_args_for_workflow() -> None:
    args = _build_args(
        task="workflow",
        query="test workflow",
        top_k=3,
        no_review=True,
        no_cluster=False,
        categories=["cs.AI"],
    )
    action, payload = _resolve_run_task_args(args)
    assert action == "research_workflow"
    assert payload["query"] == "test workflow"
    assert payload["review"] is False
    assert payload["cluster"] is True
    assert payload["top_k"] == 10
    assert payload["categories"] == ["cs.AI"]


def test_spawn_async_worker_builds_worker_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class DummyProcess:
        pid = 4242

    def fake_popen(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return DummyProcess()

    monkeypatch.setattr("paper_agent.cli.subprocess.Popen", fake_popen)

    config = AppConfig(data_dir=tmp_path / "data")
    pid, log_path = _spawn_async_worker(config=config, run_id="run_test_async")
    assert pid == 4242
    assert log_path.exists()
    command = captured["args"][0]
    assert command[-4:] == ["run", "_worker", "--run-id", "run_test_async"]


def test_cancelled_run_stops_on_execute(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path / "data")
    service = PaperAgentService(config)
    project = service.create_project(name="cancel-test", question="cancel test")

    workflow_run = service.create_run(project_id=project.project_id, action="build_index")
    cancelled_run = service.cancel_run(workflow_run.run_id, reason="test cancelled")
    assert cancelled_run.status.value == "failed"
    assert cancelled_run.state_payload.get("cancelled") is True

    with pytest.raises(RuntimeError, match="Run cancelled"):
        service.execute_run(workflow_run.run_id)

