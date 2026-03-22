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

This module implements the paper DAO for Paper Agent.
"""


from paper_agent.models.entities import Paper
from paper_agent.store.sqlite_store import SQLiteStore


class PaperDao:
    """
    PaperDao
    --------
    DAO for paper persistence and project linkage.
    """

    def __init__(self, sqlite_store: SQLiteStore) -> None:
        """
        Function Function:

            Initialize paper DAO.
        """

        self.sqlite_store = sqlite_store

    def upsert_paper(self, paper: Paper) -> Paper:
        """
        Function Function:

            Insert or update paper record.
        """

        self.sqlite_store.execute(
            """
            INSERT INTO papers(
                paper_id, source, source_key, title, authors_json, abstract, published_at, doi, arxiv_id,
                pdf_path, tags_json, status, metadata_json, content_text, created_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(paper_id) DO UPDATE SET
                source=excluded.source,
                source_key=excluded.source_key,
                title=excluded.title,
                authors_json=excluded.authors_json,
                abstract=excluded.abstract,
                published_at=excluded.published_at,
                doi=excluded.doi,
                arxiv_id=excluded.arxiv_id,
                pdf_path=excluded.pdf_path,
                tags_json=excluded.tags_json,
                status=excluded.status,
                metadata_json=excluded.metadata_json,
                content_text=excluded.content_text
            """,
            (
                paper.paper_id,
                paper.source,
                paper.source_key,
                paper.title,
                self.sqlite_store.dumps(paper.authors),
                paper.abstract,
                paper.published_at.isoformat() if paper.published_at else None,
                paper.doi,
                paper.arxiv_id,
                paper.pdf_path,
                self.sqlite_store.dumps(paper.tags),
                paper.status.value,
                self.sqlite_store.dumps(paper.metadata),
                paper.content_text,
                paper.created_at.isoformat(),
            ),
        )
        return paper

    def attach_paper_to_project(self, project_id: str, paper_id: str) -> None:
        """
        Function Function:

            Attach paper to project.
        """

        self.sqlite_store.execute(
            "INSERT OR IGNORE INTO project_papers(project_id, paper_id) VALUES(?, ?)",
            (project_id, paper_id),
        )

    def get_paper(self, paper_id: str) -> Paper | None:
        """
        Function Function:

            Fetch paper by identifier.
        """

        row = self.sqlite_store.fetchone(
            "SELECT * FROM papers WHERE paper_id = ?",
            (paper_id,),
        )
        if row is None:
            return None
        return self._row_to_paper(row)

    def list_papers(self, paper_ids: list[str] | None = None) -> list[Paper]:
        """
        Function Function:

            List paper records optionally by identifiers.
        """

        if paper_ids is None:
            row_list = self.sqlite_store.fetchall("SELECT * FROM papers ORDER BY created_at")
        else:
            if not paper_ids:
                return []
            placeholder_text = ",".join("?" for _ in paper_ids)
            row_list = self.sqlite_store.fetchall(
                f"SELECT * FROM papers WHERE paper_id IN ({placeholder_text})",
                tuple(paper_ids),
            )
        return [self._row_to_paper(row) for row in row_list]

    def list_project_papers(self, project_id: str) -> list[Paper]:
        """
        Function Function:

            List papers attached to project.
        """

        row_list = self.sqlite_store.fetchall(
            """
            SELECT p.*
            FROM papers p
            JOIN project_papers pp ON p.paper_id = pp.paper_id
            WHERE pp.project_id = ?
            ORDER BY p.created_at
            """,
            (project_id,),
        )
        return [self._row_to_paper(row) for row in row_list]

    def _row_to_paper(self, row) -> Paper:
        """
        Function Function:

            Convert SQLite row to paper entity.
        """

        return Paper(
            paper_id=row["paper_id"],
            source=row["source"],
            source_key=row["source_key"],
            title=row["title"],
            authors=self.sqlite_store.loads(row["authors_json"], []),
            abstract=row["abstract"],
            published_at=row["published_at"],
            doi=row["doi"],
            arxiv_id=row["arxiv_id"],
            pdf_path=row["pdf_path"],
            tags=self.sqlite_store.loads(row["tags_json"], []),
            status=row["status"],
            metadata=self.sqlite_store.loads(row["metadata_json"], {}),
            content_text=row["content_text"],
            created_at=row["created_at"],
        )


###################################################################################################
###################################################################################################
### End of file
