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

This module defines the unified enumerations used by Paper Agent.

The enums provide stable state names for:

- project interaction modes
- persistent entity status
- workflow run stages and states
- analysis task types and target scopes

Description of Class and Function
--------------------------------
(1) ProjectMode
    - Interaction mode enum

(2) EntityStatus
    - Persistent paper indexing status

(3) RunStatus
    - Workflow execution result status

(4) RunStage
    - Workflow execution stage enum

(5) TaskType
    - Analysis task type enum

(6) TargetType
    - Result target scope enum

(7) EvidenceRole
    - Runtime evidence semantic role enum
"""


from enum import Enum


class ProjectMode(str, Enum):
    """
    ProjectMode
    -----------
    Research interaction mode enum.
    """

    CHAT = "chat"
    WORKFLOW = "workflow"
    WORKSPACE = "workspace"


class EntityStatus(str, Enum):
    """
    EntityStatus
    ------------
    Persistent entity status enum.
    """

    DRAFT = "draft"
    INDEXED = "indexed"
    FAILED = "failed"


class RunStatus(str, Enum):
    """
    RunStatus
    ---------
    Workflow run status enum.
    """

    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class RunStage(str, Enum):
    """
    RunStage
    --------
    Workflow stage enum.
    """

    DRAFT = "DRAFT"
    SEARCHING = "SEARCHING"
    SYNCING_LIBRARY = "SYNCING_LIBRARY"
    PARSING = "PARSING"
    INDEXING = "INDEXING"
    CLUSTERING = "CLUSTERING"
    ANALYZING = "ANALYZING"
    DONE = "DONE"
    FAILED = "FAILED"


class TaskType(str, Enum):
    """
    TaskType
    --------
    Analysis task type enum.
    """

    SUMMARY = "summary"
    QA = "qa"
    REVIEW = "review"
    COMPARE = "compare"
    CLUSTER = "cluster"


class TargetType(str, Enum):
    """
    TargetType
    ----------
    Result target type enum.
    """

    PAPER = "paper"
    COLLECTION = "collection"
    CLUSTER = "cluster"


class EvidenceRole(str, Enum):
    """
    EvidenceRole
    ------------
    Runtime evidence role enum.
    """

    SUPPORT = "support"
    CONTRAST = "contrast"
    LIMITATION = "limitation"
    METHOD = "method"
    RESULT = "result"


###################################################################################################
###################################################################################################
### End of file
