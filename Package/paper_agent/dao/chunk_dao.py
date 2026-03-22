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

This module implements the chunk DAO for Paper Agent.
"""


from paper_agent.models.entities import PaperChunk
from paper_agent.store.sqlite_store import SQLiteStore
from paper_agent.utils.text_cleaner import tokenize


class ChunkDao:
    """
    ChunkDao
    --------
    DAO for chunk persistence.
    """

    def __init__(self, sqlite_store: SQLiteStore) -> None:
        """
        Function Function:

            Initialize chunk DAO.
        """

        self.sqlite_store = sqlite_store

    def replace_chunks(self, paper_id: str, chunk_list: list[PaperChunk]) -> list[PaperChunk]:
        """
        Function Function:

            Replace all chunks for a paper.
        """

        self.sqlite_store.execute("DELETE FROM chunks WHERE paper_id = ?", (paper_id,))
        self.sqlite_store.execute("DELETE FROM chunks_fts WHERE paper_id = ?", (paper_id,))
        parameter_list = []
        fts_parameter_list = []
        for item in chunk_list:
            parameter_list.append(
                (
                    item.chunk_id,
                    item.paper_id,
                    item.section_title,
                    item.chunk_index,
                    item.content,
                    item.page_start,
                    item.page_end,
                    item.token_count,
                    self.sqlite_store.dumps(item.citation_markers),
                )
            )
            fts_parameter_list.append(
                (
                    item.chunk_id,
                    item.paper_id,
                    item.section_title,
                    item.content,
                )
            )
        if parameter_list:
            self.sqlite_store.executemany(
                """
                INSERT INTO chunks(
                    chunk_id, paper_id, section_title, chunk_index, content, page_start, page_end, token_count, citation_markers_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                parameter_list,
            )
            self.sqlite_store.executemany(
                "INSERT INTO chunks_fts(chunk_id, paper_id, section_title, content) VALUES(?, ?, ?, ?)",
                fts_parameter_list,
            )
        return chunk_list

    def search_project_chunks(self, project_id: str, query: str, limit: int = 10) -> list[dict]:
        """
        Search project chunks with SQLite FTS5 lexical retrieval.
        """

        fts_query = self._build_fts_query(query)
        if not fts_query:
            return []

        row_list = self.sqlite_store.fetchall(
            """
            SELECT
                c.chunk_id,
                c.content,
                c.section_title,
                c.page_start,
                c.page_end,
                c.paper_id,
                p.title AS paper_title,
                bm25(chunks_fts) AS bm25_score
            FROM chunks_fts
            JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
            JOIN project_papers pp ON pp.paper_id = c.paper_id
            JOIN papers p ON p.paper_id = c.paper_id
            WHERE pp.project_id = ?
              AND chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts), c.chunk_index
            LIMIT ?
            """,
            (project_id, fts_query, limit),
        )
        ranked_item_list: list[dict] = []
        for row in row_list:
            bm25_score = float(row["bm25_score"])
            lexical_score = 1.0 / (1.0 + max(0.0, bm25_score))
            ranked_item_list.append(
                {
                    "chunk_id": row["chunk_id"],
                    "document": row["content"],
                    "metadata": {
                        "paper_id": row["paper_id"],
                        "paper_title": row["paper_title"],
                        "section_title": row["section_title"],
                        "page_start": row["page_start"],
                        "page_end": row["page_end"],
                    },
                    "bm25_score": bm25_score,
                    "score": lexical_score,
                    "retrieval_channel": "fts",
                }
            )
        return ranked_item_list

    def _build_fts_query(self, query: str) -> str:
        token_list = tokenize(query)
        escaped_token_list = [token.replace('"', '""') for token in token_list]
        if not escaped_token_list:
            return ""
        return " OR ".join(f'"{token}"' for token in escaped_token_list)

    def list_chunks_for_paper(self, paper_id: str) -> list[PaperChunk]:
        """
        Function Function:

            List chunks for one paper.
        """

        row_list = self.sqlite_store.fetchall(
            "SELECT * FROM chunks WHERE paper_id = ? ORDER BY chunk_index",
            (paper_id,),
        )
        return [self._row_to_chunk(row) for row in row_list]

    def list_chunks_for_project(self, project_id: str) -> list[PaperChunk]:
        """
        Function Function:

            List chunks for all papers in a project.
        """

        row_list = self.sqlite_store.fetchall(
            """
            SELECT c.*
            FROM chunks c
            JOIN project_papers pp ON c.paper_id = pp.paper_id
            WHERE pp.project_id = ?
            ORDER BY c.paper_id, c.chunk_index
            """,
            (project_id,),
        )
        return [self._row_to_chunk(row) for row in row_list]

    def _row_to_chunk(self, row) -> PaperChunk:
        """
        Function Function:

            Convert SQLite row to chunk entity.
        """

        return PaperChunk(
            chunk_id=row["chunk_id"],
            paper_id=row["paper_id"],
            section_title=row["section_title"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            page_start=row["page_start"],
            page_end=row["page_end"],
            token_count=row["token_count"],
            citation_markers=self.sqlite_store.loads(row["citation_markers_json"], []),
        )


###################################################################################################
###################################################################################################
### End of file
