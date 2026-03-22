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

This module defines the LangGraph workflow state for Paper Agent.
"""


from typing import Any
from typing_extensions import TypedDict


class ResearchWorkflowState(TypedDict, total=False):
    """
    ResearchWorkflowState
    ---------------------
    State payload shared across LangGraph nodes.
    """

    run_id: str
    project_id: str
    action: str
    query: str
    limit: int
    top_k: int
    review: bool
    cluster: bool
    author: str
    categories: list[str]
    from_year: int
    to_year: int
    resumed_from_run_id: str
    resume_from_stage: str
    last_checkpoint_stage: str
    provider: str
    library_path: str
    collection_id: str
    library_options: dict[str, Any]
    payload: Any
    paper_id_list: list[str]
    cluster_id_list: list[str]
    error: str


###################################################################################################
###################################################################################################
### End of file
