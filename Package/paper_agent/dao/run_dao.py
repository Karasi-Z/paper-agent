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

This module implements the workflow run DAO for Paper Agent.
"""


from paper_agent.models.entities import WorkflowRun
from paper_agent.store.sqlite_store import SQLiteStore


class RunDao:
    """
    RunDao
    ------
    DAO for workflow run persistence.
    """

    def __init__(self, sqlite_store: SQLiteStore) -> None:
        """
        Function Function:

            Initialize run DAO.
        """

        self.sqlite_store = sqlite_store

    def upsert_run(self, workflow_run: WorkflowRun) -> WorkflowRun:
        """
        Function Function:

            Insert or update workflow run record.
        """

        self.sqlite_store.execute(
            """
            INSERT INTO runs(run_id, project_id, stage, status, state_json, error, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                stage=excluded.stage,
                status=excluded.status,
                state_json=excluded.state_json,
                error=excluded.error,
                updated_at=excluded.updated_at
            """,
            (
                workflow_run.run_id,
                workflow_run.project_id,
                workflow_run.stage.value,
                workflow_run.status.value,
                self.sqlite_store.dumps(workflow_run.state_payload),
                workflow_run.error,
                workflow_run.created_at.isoformat(),
                workflow_run.updated_at.isoformat(),
            ),
        )
        return workflow_run

    def get_run(self, run_id: str) -> WorkflowRun | None:
        """
        Function Function:

            Fetch workflow run by identifier.
        """

        row = self.sqlite_store.fetchone(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        )
        if row is None:
            return None

        return WorkflowRun(
            run_id=row["run_id"],
            project_id=row["project_id"],
            stage=row["stage"],
            status=row["status"],
            state_payload=self.sqlite_store.loads(row["state_json"], {}),
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


###################################################################################################
###################################################################################################
### End of file
