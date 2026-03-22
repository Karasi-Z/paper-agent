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

This module implements the workflow run event DAO for Paper Agent.
"""


from paper_agent.models.entities import RunEvent
from paper_agent.store.sqlite_store import SQLiteStore


class RunEventDao:
    """
    RunEventDao
    -----------
    DAO for workflow event persistence.
    """

    def __init__(self, sqlite_store: SQLiteStore) -> None:
        """
        Function Function:

            Initialize run event DAO.
        """

        self.sqlite_store = sqlite_store

    def insert_event(self, run_event: RunEvent) -> RunEvent:
        """
        Function Function:

            Insert one workflow event record.
        """

        self.sqlite_store.execute(
            """
            INSERT INTO run_events(run_id, project_id, event_name, stage, progress, message, payload_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_event.run_id,
                run_event.project_id,
                run_event.event_name,
                run_event.stage.value if run_event.stage else None,
                run_event.progress,
                run_event.message,
                self.sqlite_store.dumps(run_event.payload),
                run_event.created_at.isoformat(),
            ),
        )
        row = self.sqlite_store.fetchone(
            "SELECT event_id FROM run_events WHERE run_id = ? ORDER BY event_id DESC LIMIT 1",
            (run_event.run_id,),
        )
        if row is not None:
            run_event.event_id = int(row["event_id"])
        return run_event

    def list_events(self, run_id: str) -> list[RunEvent]:
        """
        Function Function:

            List workflow events for one run.
        """

        row_list = self.sqlite_store.fetchall(
            "SELECT * FROM run_events WHERE run_id = ? ORDER BY event_id",
            (run_id,),
        )
        return [self._row_to_event(row) for row in row_list]

    def _row_to_event(self, row) -> RunEvent:
        """
        Function Function:

            Convert SQLite row to run event entity.
        """

        return RunEvent(
            event_id=row["event_id"],
            run_id=row["run_id"],
            project_id=row["project_id"],
            event_name=row["event_name"],
            stage=row["stage"],
            progress=row["progress"],
            message=row["message"],
            payload=self.sqlite_store.loads(row["payload_json"], {}),
            created_at=row["created_at"],
        )


###################################################################################################
###################################################################################################
### End of file
