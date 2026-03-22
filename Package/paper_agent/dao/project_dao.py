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

This module implements the project DAO for Paper Agent.
"""


from paper_agent.models.entities import ResearchProject
from paper_agent.store.sqlite_store import SQLiteStore


class ProjectDao:
    """
    ProjectDao
    ----------
    DAO for research project persistence.
    """

    def __init__(self, sqlite_store: SQLiteStore) -> None:
        """
        Function Function:

            Initialize project DAO.
        """

        self.sqlite_store = sqlite_store

    def upsert_project(self, project: ResearchProject) -> ResearchProject:
        """
        Function Function:

            Insert or update project record.
        """

        self.sqlite_store.execute(
            """
            INSERT INTO projects(project_id, name, question, mode, status, settings_json, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                name=excluded.name,
                question=excluded.question,
                mode=excluded.mode,
                status=excluded.status,
                settings_json=excluded.settings_json,
                updated_at=excluded.updated_at
            """,
            (
                project.project_id,
                project.name,
                project.question,
                project.mode.value,
                project.status.value,
                self.sqlite_store.dumps(project.settings),
                project.created_at.isoformat(),
                project.updated_at.isoformat(),
            ),
        )
        return project

    def get_project(self, project_id: str) -> ResearchProject | None:
        """
        Function Function:

            Fetch project by identifier.
        """

        row = self.sqlite_store.fetchone(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,),
        )
        if row is None:
            return None

        return ResearchProject(
            project_id=row["project_id"],
            name=row["name"],
            question=row["question"],
            mode=row["mode"],
            status=row["status"],
            settings=self.sqlite_store.loads(row["settings_json"], {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_projects(self) -> list[ResearchProject]:
        """
        Function Function:

            List all projects ordered by update time.
        """

        row_list = self.sqlite_store.fetchall(
            "SELECT * FROM projects ORDER BY updated_at DESC, created_at DESC",
        )
        return [
            ResearchProject(
                project_id=row["project_id"],
                name=row["name"],
                question=row["question"],
                mode=row["mode"],
                status=row["status"],
                settings=self.sqlite_store.loads(row["settings_json"], {}),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in row_list
        ]


###################################################################################################
###################################################################################################
### End of file
