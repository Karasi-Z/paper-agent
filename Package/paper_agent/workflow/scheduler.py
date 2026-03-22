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

This module implements the workflow scheduler wrapper for Paper Agent.
"""


from paper_agent.workflow.graph import ResearchWorkflowGraph
from paper_agent.workflow.state import ResearchWorkflowState


class WorkflowScheduler:
    """
    WorkflowScheduler
    -----------------
    Thin scheduler wrapper over compiled LangGraph workflow.
    """

    def __init__(self, workflow_graph: ResearchWorkflowGraph) -> None:
        """
        Function Function:

            Initialize workflow scheduler.
        """

        self.workflow_graph = workflow_graph

    def run(self, workflow_state: ResearchWorkflowState) -> ResearchWorkflowState:
        """
        Function Function:

            Execute compiled workflow graph.
        """

        return self.workflow_graph.invoke(workflow_state)


###################################################################################################
###################################################################################################
### End of file
