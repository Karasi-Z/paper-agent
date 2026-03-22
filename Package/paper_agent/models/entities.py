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

This module defines the domain entities used by Paper Agent.

The entities are shared by:

- SQLite business persistence
- Chroma vector indexing
- LangGraph workflow state transition
- Agent input and output contracts
- FastAPI response serialization

Description of Class and Function
--------------------------------
(1) ResearchProject
    - Research task root aggregate

(2) Paper / PaperChunk / EmbeddingVector
    - Literature indexing entities

(3) Cluster / AnalysisResult / WorkflowRun / RunEvent
    - Analysis output and workflow tracking entities

(4) OperationResult / ProjectSnapshot
    - Service-level transport entities
"""


from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from paper_agent.models.enums import EvidenceRole, EntityStatus, ProjectMode, RunStage, RunStatus, TargetType, TaskType


def utc_now() -> datetime:
    """
    Function Function:

        Return current UTC timestamp.
    """

    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    """
    Function Function:

        Generate a prefixed unique identifier.
    """

    return f"{prefix}_{uuid4().hex}"


class ResearchProject(BaseModel):
    """
    ResearchProject
    ---------------
    Research project aggregate root.
    """

    project_id: str = Field(default_factory=lambda: new_id("proj"))
    name: str
    question: str
    mode: ProjectMode = ProjectMode.WORKFLOW
    status: RunStatus = RunStatus.RUNNING
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Paper(BaseModel):
    """
    Paper
    -----
    Unified paper entity.
    """

    paper_id: str = Field(default_factory=lambda: new_id("paper"))
    source: str = "local"
    source_key: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    published_at: datetime | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    pdf_path: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: EntityStatus = EntityStatus.DRAFT
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_text: str = ""
    created_at: datetime = Field(default_factory=utc_now)


class PaperChunk(BaseModel):
    """
    PaperChunk
    ----------
    Chunk entity for retrieval and evidence tracing.
    """

    chunk_id: str = Field(default_factory=lambda: new_id("chunk"))
    paper_id: str
    section_title: str = "body"
    chunk_index: int
    content: str
    page_start: int | None = None
    page_end: int | None = None
    token_count: int = 0
    citation_markers: list[str] = Field(default_factory=list)


class EmbeddingVector(BaseModel):
    """
    EmbeddingVector
    ---------------
    Embedding payload entity.
    """

    vector_id: str = Field(default_factory=lambda: new_id("vec"))
    object_type: str
    object_id: str
    model_name: str
    dim: int
    values: list[float]
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceCitation(BaseModel):
    """
    EvidenceCitation
    ----------------
    Evidence citation entity.
    """

    paper_id: str
    chunk_id: str
    paper_title: str
    quote: str
    page_hint: str | None = None
    score: float = 0.0


class Evidence(BaseModel):
    """
    Evidence
    --------
    Runtime evidence object used for retrieval, reranking, and packing.
    """

    evidence_id: str = Field(default_factory=lambda: new_id("evd"))
    paper_id: str
    chunk_id: str
    paper_title: str
    section_title: str = "body"
    quote: str
    page_start: int | None = None
    page_end: int | None = None
    retrieval_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0
    role: EvidenceRole = EvidenceRole.SUPPORT
    reason: str = ""


class Cluster(BaseModel):
    """
    Cluster
    -------
    Topic cluster entity.
    """

    cluster_id: str = Field(default_factory=lambda: new_id("cluster"))
    project_id: str
    label: str
    paper_ids: list[str]
    keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    representative_papers: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class AnalysisResult(BaseModel):
    """
    AnalysisResult
    --------------
    Analysis output entity.
    """

    result_id: str = Field(default_factory=lambda: new_id("result"))
    project_id: str
    task_type: TaskType
    target_type: TargetType
    target_id: str
    content_md: str
    content_json: dict[str, Any] = Field(default_factory=dict)
    citations: list[EvidenceCitation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class WorkflowRun(BaseModel):
    """
    WorkflowRun
    -----------
    Workflow execution tracking entity.
    """

    run_id: str = Field(default_factory=lambda: new_id("run"))
    project_id: str
    stage: RunStage
    status: RunStatus = RunStatus.RUNNING
    state_payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RunEvent(BaseModel):
    """
    RunEvent
    --------
    Workflow event stream entity.
    """

    event_id: int | None = None
    run_id: str
    project_id: str
    event_name: str
    stage: RunStage | None = None
    progress: float | None = None
    message: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class DocumentParseResult(BaseModel):
    """
    DocumentParseResult
    -------------------
    Structured document parsing result.
    """

    title: str
    abstract: str = ""
    full_text: str
    sections: list[dict[str, str]] = Field(default_factory=list)


class LibraryItem(BaseModel):
    """
    LibraryItem
    -----------
    Unified literature-manager item.
    """

    item_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    tags: list[str] = Field(default_factory=list)
    attachment_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectSnapshot(BaseModel):
    """
    ProjectSnapshot
    ---------------
    Full project snapshot entity.
    """

    project: ResearchProject
    papers: list[Paper] = Field(default_factory=list)
    clusters: list[Cluster] = Field(default_factory=list)
    analyses: list[AnalysisResult] = Field(default_factory=list)


class OperationResult(BaseModel):
    """
    OperationResult
    ---------------
    Service operation envelope.
    """

    run: WorkflowRun
    payload: Any


###################################################################################################
###################################################################################################
### End of file
