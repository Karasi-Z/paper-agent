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

This module implements the analysis DAO for Paper Agent.
"""


from paper_agent.models.entities import AnalysisResult
from paper_agent.store.sqlite_store import SQLiteStore


class AnalysisDao:
    """
    AnalysisDao
    -----------
    DAO for analysis result persistence.
    """

    def __init__(self, sqlite_store: SQLiteStore) -> None:
        """
        Function Function:

            Initialize analysis DAO.
        """

        self.sqlite_store = sqlite_store

    def upsert_analysis(self, analysis_result: AnalysisResult) -> AnalysisResult:
        """
        Function Function:

            Insert or update analysis result.
        """

        self.sqlite_store.execute(
            """
            INSERT INTO analyses(result_id, project_id, task_type, target_type, target_id, content_md, content_json, citations_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(result_id) DO UPDATE SET
                content_md=excluded.content_md,
                content_json=excluded.content_json,
                citations_json=excluded.citations_json
            """,
            (
                analysis_result.result_id,
                analysis_result.project_id,
                analysis_result.task_type.value,
                analysis_result.target_type.value,
                analysis_result.target_id,
                analysis_result.content_md,
                self.sqlite_store.dumps(analysis_result.content_json),
                self.sqlite_store.dumps([item.model_dump(mode="json") for item in analysis_result.citations]),
                analysis_result.created_at.isoformat(),
            ),
        )
        return analysis_result

    def list_analyses(self, project_id: str) -> list[AnalysisResult]:
        """
        Function Function:

            List analysis results for project.
        """

        row_list = self.sqlite_store.fetchall(
            "SELECT * FROM analyses WHERE project_id = ? ORDER BY created_at",
            (project_id,),
        )
        result_list: list[AnalysisResult] = []
        for row in row_list:
            result_list.append(
                AnalysisResult(
                    result_id=row["result_id"],
                    project_id=row["project_id"],
                    task_type=row["task_type"],
                    target_type=row["target_type"],
                    target_id=row["target_id"],
                    content_md=row["content_md"],
                    content_json=self.sqlite_store.loads(row["content_json"], {}),
                    citations=self.sqlite_store.loads(row["citations_json"], []),
                    created_at=row["created_at"],
                )
            )
        return result_list


###################################################################################################
###################################################################################################
### End of file
