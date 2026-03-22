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

This module defines API schemas for Paper Agent.

The schemas are intentionally separate from persistent entities so that
external contracts remain stable even if internal entities evolve.

Description of Class and Function
--------------------------------
(1) CreateProjectRequest
    - Create research project request schema

(2) SearchRequest / AskRequest
    - Search and QA request schemas

(3) ImportTextRequest / ImportFileRequest / LibrarySyncRequest
    - Paper import and library synchronization schemas

(4) PushNoteRequest / ResearchWorkflowRequest
    - Literature note push and workflow schemas
"""


from pydantic import BaseModel, Field

from paper_agent.models.enums import ProjectMode


class CreateProjectRequest(BaseModel):
    """
    CreateProjectRequest
    --------------------
    Project creation request schema.
    """

    name: str
    question: str
    mode: ProjectMode = ProjectMode.WORKFLOW
    settings: dict = Field(default_factory=dict)


class SearchRequest(BaseModel):
    """
    SearchRequest
    -------------
    Search request schema.
    """

    query: str
    limit: int = 10
    author: str | None = None
    categories: list[str] = Field(default_factory=list)
    from_year: int | None = None
    to_year: int | None = None


class ImportTextRequest(BaseModel):
    """
    ImportTextRequest
    -----------------
    Raw text paper import request schema.
    """

    title: str
    content: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    tags: list[str] = Field(default_factory=list)


class ImportFileRequest(BaseModel):
    """
    ImportFileRequest
    -----------------
    File-based paper import request schema.
    """

    path: str
    title: str | None = None


class AskRequest(BaseModel):
    """
    AskRequest
    ----------
    Question answering request schema.
    """

    query: str
    top_k: int | None = None


class LibrarySyncRequest(BaseModel):
    """
    LibrarySyncRequest
    ------------------
    Literature manager synchronization request schema.
    """

    provider: str
    library_path: str
    collection_id: str | None = None
    mode: str | None = None
    library_type: str | None = None
    library_id: str | None = None
    api_key: str | None = None
    base_url: str | None = None


class PushNoteRequest(BaseModel):
    """
    PushNoteRequest
    ---------------
    Literature note push request schema.
    """

    provider: str
    library_path: str = ""
    paper_id: str | None = None
    item_id: str | None = None
    note_md: str | None = None
    result_id: str | None = None
    prefer_task_type: str | None = "review"
    mode: str | None = None
    library_type: str | None = None
    library_id: str | None = None
    api_key: str | None = None
    base_url: str | None = None


class ResearchWorkflowRequest(BaseModel):
    """
    ResearchWorkflowRequest
    -----------------------
    End-to-end research workflow request schema.
    """

    query: str | None = None
    review: bool = True
    cluster: bool = True
    limit: int = 10
    author: str | None = None
    categories: list[str] = Field(default_factory=list)
    from_year: int | None = None
    to_year: int | None = None


class AutoRouteRequest(BaseModel):
    """
    Auto-route request schema.
    """

    query: str = ""
    limit: int = 10
    top_k: int | None = None


###################################################################################################
###################################################################################################
### End of file
