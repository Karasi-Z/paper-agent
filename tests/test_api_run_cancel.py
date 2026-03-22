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

This module implements API tests for run cancel endpoint contract.
"""


from pathlib import Path

from fastapi.testclient import TestClient

from paper_agent.config import AppConfig
from paper_agent.server import create_app


def test_api_cancel_run_contract(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path / "data")
    app = create_app(config)
    service = app.state.service

    project = service.create_project(name="api-cancel-test", question="cancel endpoint contract")
    workflow_run = service.create_run(project_id=project.project_id, action="build_index")

    with TestClient(app) as client:
        response = client.post(
            f"/api/runs/{workflow_run.run_id}/cancel",
            params={"reason": "api cancel test"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == workflow_run.run_id
    assert payload["project_id"] == project.project_id
    assert payload["status"] == "failed"
    assert payload["stage"] == "FAILED"
    assert payload["error"] == "api cancel test"
    assert payload["state_payload"]["cancelled"] is True
    assert payload["state_payload"]["cancel_reason"] == "api cancel test"


def test_api_cancel_unknown_run_returns_404(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path / "data")
    app = create_app(config)

    with TestClient(app) as client:
        response = client.post("/api/runs/run_not_exists/cancel")

    assert response.status_code == 404
    assert "Unknown run_id" in response.json()["detail"]

