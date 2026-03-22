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

This module implements run workspace persistence helpers for Paper Agent.

Description of Class and Function
--------------------------------
(1) RunWorkspaceStore
    - Persist run state, checkpoint, and artifact files
"""


import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_agent.utils.file_lock import FileLock


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunWorkspaceStore:
    """
    Manage run-scoped workspace files for state, checkpoints, and artifacts.
    """

    def __init__(self, data_dir: Path) -> None:
        self.workspace_root = data_dir / "workspace" / "projects"
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def ensure_run_workspace(self, project_id: str, run_id: str, action: str, payload: dict[str, Any] | None = None) -> Path:
        run_dir = self._run_dir(project_id, run_id)
        project_dir = self._project_dir(project_id)
        with self._lock:
            (project_dir / "indexes").mkdir(parents=True, exist_ok=True)
            (project_dir / "exports").mkdir(parents=True, exist_ok=True)
            (run_dir / "logs").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "tmp").mkdir(parents=True, exist_ok=True)
            manifest_path = run_dir / "manifest.json"
            if not manifest_path.exists():
                manifest_path.write_text(
                    json.dumps(
                        {
                            "project_id": project_id,
                            "run_id": run_id,
                            "action": action,
                            "created_at": utc_now_iso(),
                            "payload": payload or {},
                        },
                        ensure_ascii=False,
                        indent=2,
                        default=str,
                    ),
                    encoding="utf-8",
                )
        return run_dir

    def write_state(
        self,
        project_id: str,
        run_id: str,
        state_payload: dict[str, Any],
        stage: str,
        status: str,
        lifecycle: str,
        error: str | None = None,
    ) -> None:
        state_path = self._run_dir(project_id, run_id) / "state.json"
        state_doc = {
            "project_id": project_id,
            "run_id": run_id,
            "stage": stage,
            "status": status,
            "lifecycle": lifecycle,
            "error": error,
            "updated_at": utc_now_iso(),
            "state_payload": state_payload,
        }
        with self._lock:
            state_path.write_text(json.dumps(state_doc, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def write_checkpoint(self, project_id: str, run_id: str, stage: str, payload: dict[str, Any]) -> None:
        checkpoint_path = self._run_dir(project_id, run_id) / "artifacts" / f"checkpoint_{stage}.json"
        with self._lock:
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "project_id": project_id,
                        "run_id": run_id,
                        "stage": stage,
                        "created_at": utc_now_iso(),
                        "payload": payload,
                    },
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

    def write_artifact(self, project_id: str, run_id: str, relative_path: str, payload: Any) -> None:
        artifact_path = self._run_dir(project_id, run_id) / "artifacts" / relative_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def write_text_artifact(self, project_id: str, run_id: str, relative_path: str, content: str) -> Path:
        artifact_path = self._run_dir(project_id, run_id) / "artifacts" / relative_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            artifact_path.write_text(content, encoding="utf-8")
        return artifact_path

    def write_project_export(self, project_id: str, filename: str, content: str) -> Path:
        export_path = self._project_dir(project_id) / "exports" / filename
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            export_path.write_text(content, encoding="utf-8")
        return export_path

    def project_lock(self, project_id: str, timeout_seconds: float = 20.0) -> FileLock:
        return FileLock(self._project_dir(project_id) / "project.lock", timeout_seconds=timeout_seconds)

    def resource_lock(self, project_id: str, resource_name: str, timeout_seconds: float = 20.0) -> FileLock:
        return FileLock(self._project_dir(project_id) / f"{resource_name}.lock", timeout_seconds=timeout_seconds)

    def export_path(self, project_id: str, filename: str) -> Path:
        return self._project_dir(project_id) / "exports" / filename

    def project_dir(self, project_id: str) -> Path:
        return self._project_dir(project_id)

    def write_error_report(
        self,
        project_id: str,
        run_id: str,
        failed_stage: str,
        error: str,
        last_event_message: str | None = None,
    ) -> None:
        report_path = self._run_dir(project_id, run_id) / "artifacts" / "error_report.md"
        line_list = [
            "# Error Report",
            "",
            f"- project_id: `{project_id}`",
            f"- run_id: `{run_id}`",
            f"- failed_stage: `{failed_stage}`",
            f"- generated_at: `{utc_now_iso()}`",
            "",
            "## Error",
            "```text",
            error,
            "```",
        ]
        if last_event_message:
            line_list.extend(
                [
                    "",
                    "## Last Event",
                    last_event_message,
                ]
            )
        with self._lock:
            report_path.write_text("\n".join(line_list).strip() + "\n", encoding="utf-8")

    def _run_dir(self, project_id: str, run_id: str) -> Path:
        return self.workspace_root / project_id / "runs" / run_id

    def _project_dir(self, project_id: str) -> Path:
        return self.workspace_root / project_id
