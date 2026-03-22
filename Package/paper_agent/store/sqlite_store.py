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

This module implements the SQLite business store for Paper Agent.

The store manages:

- project metadata
- paper metadata and project linkage
- chunk metadata
- analysis result persistence
- cluster persistence
    - workflow run persistence
    - workflow event persistence

Description of Class and Function
--------------------------------
(1) SQLiteStore
    - SQLite connection and schema management
"""


import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class SQLiteStore:
    """
    SQLiteStore
    -----------
    SQLite persistence store for business entities.
    """

    def __init__(self, db_path: str | Path) -> None:
        """
        Function Function:

            Initialize SQLite store and schema.
        """

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        """
        Function Function:

            Create SQLite connection with row factory.
        """

        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def execute(self, sql: str, parameters: list | tuple | None = None) -> None:
        """
        Function Function:

            Execute write SQL statement.
        """

        with self._lock, self.connect() as connection:
            connection.execute(sql, parameters or [])
            connection.commit()

    def executemany(self, sql: str, parameter_list: list[tuple]) -> None:
        """
        Function Function:

            Execute batch write SQL statement.
        """

        with self._lock, self.connect() as connection:
            connection.executemany(sql, parameter_list)
            connection.commit()

    def fetchone(self, sql: str, parameters: list | tuple | None = None) -> sqlite3.Row | None:
        """
        Function Function:

            Execute query and fetch one row.
        """

        with self.connect() as connection:
            return connection.execute(sql, parameters or []).fetchone()

    def fetchall(self, sql: str, parameters: list | tuple | None = None) -> list[sqlite3.Row]:
        """
        Function Function:

            Execute query and fetch all rows.
        """

        with self.connect() as connection:
            row_list = connection.execute(sql, parameters or []).fetchall()
        return list(row_list)

    def dumps(self, value: Any) -> str:
        """
        Function Function:

            Serialize Python object to JSON string.
        """

        return json.dumps(value, ensure_ascii=False, default=str)

    def loads(self, value: str | None, default: Any) -> Any:
        """
        Function Function:

            Deserialize JSON string with default fallback.
        """

        if not value:
            return default
        return json.loads(value)

    def _init_schema(self) -> None:
        """
        Function Function:

            Initialize SQLite schema used by Paper Agent.
        """

        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    question TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    settings_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS papers (
                    paper_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_key TEXT,
                    title TEXT NOT NULL,
                    authors_json TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    published_at TEXT,
                    doi TEXT,
                    arxiv_id TEXT,
                    pdf_path TEXT,
                    tags_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    content_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS project_papers (
                    project_id TEXT NOT NULL,
                    paper_id TEXT NOT NULL,
                    PRIMARY KEY (project_id, paper_id)
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    paper_id TEXT NOT NULL,
                    section_title TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    page_start INTEGER,
                    page_end INTEGER,
                    token_count INTEGER NOT NULL,
                    citation_markers_json TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    paper_id UNINDEXED,
                    section_title,
                    content,
                    tokenize='unicode61'
                );

                CREATE TABLE IF NOT EXISTS analyses (
                    result_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    content_md TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS clusters (
                    cluster_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    paper_ids_json TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    representative_papers_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS run_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    stage TEXT,
                    progress REAL,
                    message TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_run_events_run_id
                ON run_events(run_id, event_id);

                CREATE INDEX IF NOT EXISTS idx_project_papers_project_id
                ON project_papers(project_id, paper_id);
                """
            )
            connection.commit()


###################################################################################################
###################################################################################################
### End of file
