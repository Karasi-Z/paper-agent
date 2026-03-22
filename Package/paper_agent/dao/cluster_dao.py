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

This module implements the cluster DAO for Paper Agent.
"""


from paper_agent.models.entities import Cluster
from paper_agent.store.sqlite_store import SQLiteStore


class ClusterDao:
    """
    ClusterDao
    ----------
    DAO for cluster persistence.
    """

    def __init__(self, sqlite_store: SQLiteStore) -> None:
        """
        Function Function:

            Initialize cluster DAO.
        """

        self.sqlite_store = sqlite_store

    def replace_clusters(self, project_id: str, cluster_list: list[Cluster]) -> list[Cluster]:
        """
        Function Function:

            Replace project cluster set.
        """

        self.sqlite_store.execute("DELETE FROM clusters WHERE project_id = ?", (project_id,))
        parameter_list = []
        for item in cluster_list:
            parameter_list.append(
                (
                    item.cluster_id,
                    item.project_id,
                    item.label,
                    self.sqlite_store.dumps(item.paper_ids),
                    self.sqlite_store.dumps(item.keywords),
                    item.summary,
                    self.sqlite_store.dumps(item.representative_papers),
                    item.created_at.isoformat(),
                )
            )
        if parameter_list:
            self.sqlite_store.executemany(
                """
                INSERT INTO clusters(
                    cluster_id, project_id, label, paper_ids_json, keywords_json, summary, representative_papers_json, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                parameter_list,
            )
        return cluster_list

    def list_clusters(self, project_id: str) -> list[Cluster]:
        """
        Function Function:

            List clusters for project.
        """

        row_list = self.sqlite_store.fetchall(
            "SELECT * FROM clusters WHERE project_id = ? ORDER BY created_at",
            (project_id,),
        )
        cluster_list: list[Cluster] = []
        for row in row_list:
            cluster_list.append(
                Cluster(
                    cluster_id=row["cluster_id"],
                    project_id=row["project_id"],
                    label=row["label"],
                    paper_ids=self.sqlite_store.loads(row["paper_ids_json"], []),
                    keywords=self.sqlite_store.loads(row["keywords_json"], []),
                    summary=row["summary"],
                    representative_papers=self.sqlite_store.loads(row["representative_papers_json"], []),
                    created_at=row["created_at"],
                )
            )
        return cluster_list


###################################################################################################
###################################################################################################
### End of file
