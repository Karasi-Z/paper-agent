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

This module defines the application configuration for Paper Agent.

Description of Class and Function
--------------------------------
(1) AppConfig
    - Unified runtime configuration model
"""


import os
from pathlib import Path

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """
    AppConfig
    ---------
    Unified runtime configuration model.
    """

    data_dir: Path = Field(default_factory=lambda: Path.cwd() / ".paper_agent_data")
    db_path: Path | None = None
    chroma_dir: Path | None = None
    notes_dir: Path | None = None
    chunk_size: int = 220
    chunk_overlap: int = 40
    vector_dim: int = 256
    default_top_k: int = 5
    max_clusters: int = 6
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:8b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    embedding_provider: str = "ollama"
    embedding_model: str = "qwen3-embedding:0.6b"
    parser_backend: str = "auto"
    grobid_url: str = "http://127.0.0.1:8070"
    agent_framework: str = "autogen"
    workflow_framework: str = "langgraph"
    vector_backend: str = "chromadb"

    def model_post_init(self, __context: object) -> None:
        """
        Function Function:

            Finalize derived directories after initialization.
        """

        if self.db_path is None:
            self.db_path = self.data_dir / "paper_agent.sqlite3"
        if self.chroma_dir is None:
            self.chroma_dir = self.data_dir / "chromadb"
        if self.notes_dir is None:
            self.notes_dir = self.data_dir / "notes"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        Function Function:

            Build configuration from environment variables.
        """

        data_dir = Path(os.getenv("PAPER_AGENT_DATA_DIR", Path.cwd() / ".paper_agent_data"))
        return cls(
            data_dir=data_dir,
            chunk_size=int(os.getenv("PAPER_AGENT_CHUNK_SIZE", "220")),
            chunk_overlap=int(os.getenv("PAPER_AGENT_CHUNK_OVERLAP", "40")),
            vector_dim=int(os.getenv("PAPER_AGENT_VECTOR_DIM", "256")),
            default_top_k=int(os.getenv("PAPER_AGENT_TOP_K", "5")),
            max_clusters=int(os.getenv("PAPER_AGENT_MAX_CLUSTERS", "6")),
            llm_provider=os.getenv("PAPER_AGENT_LLM_PROVIDER", "ollama"),
            llm_model=os.getenv("PAPER_AGENT_LLM_MODEL", "qwen3:8b"),
            ollama_base_url=os.getenv("PAPER_AGENT_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            embedding_provider=os.getenv("PAPER_AGENT_EMBEDDING_PROVIDER", "ollama"),
            embedding_model=os.getenv("PAPER_AGENT_EMBEDDING_MODEL", "qwen3-embedding:0.6b"),
            parser_backend=os.getenv("PAPER_AGENT_PARSER_BACKEND", "auto"),
            grobid_url=os.getenv("PAPER_AGENT_GROBID_URL", "http://127.0.0.1:8070"),
            agent_framework=os.getenv("PAPER_AGENT_AGENT_FRAMEWORK", "autogen"),
            workflow_framework=os.getenv("PAPER_AGENT_WORKFLOW_FRAMEWORK", "langgraph"),
            vector_backend=os.getenv("PAPER_AGENT_VECTOR_BACKEND", "chromadb"),
        )


###################################################################################################
###################################################################################################
### End of file
