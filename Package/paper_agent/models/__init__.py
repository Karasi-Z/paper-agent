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

This module exposes unified model definitions for Paper Agent.

The package is split into:

- `enums`
    workflow status, task type, and mode enumerations

- `entities`
    persistent domain entities used by DAO, workflow, and agents

- `schemas`
    API request and response schemas

Description of Class and Function
--------------------------------
(1) Re-export commonly used enums and entities
    - Simplify imports across the project
"""


from paper_agent.models.entities import (
    AnalysisResult,
    Cluster,
    DocumentParseResult,
    EmbeddingVector,
    Evidence,
    EvidenceCitation,
    LibraryItem,
    OperationResult,
    Paper,
    PaperChunk,
    ProjectSnapshot,
    ResearchProject,
    WorkflowRun,
    new_id,
    utc_now,
)
from paper_agent.models.enums import EvidenceRole, EntityStatus, ProjectMode, RunStage, RunStatus, TargetType, TaskType

__all__ = [
    "AnalysisResult",
    "Cluster",
    "DocumentParseResult",
    "EmbeddingVector",
    "Evidence",
    "EvidenceRole",
    "EntityStatus",
    "EvidenceCitation",
    "LibraryItem",
    "OperationResult",
    "Paper",
    "PaperChunk",
    "ProjectMode",
    "ProjectSnapshot",
    "ResearchProject",
    "RunStage",
    "RunStatus",
    "TargetType",
    "TaskType",
    "WorkflowRun",
    "new_id",
    "utc_now",
]


###################################################################################################
###################################################################################################
### End of file
