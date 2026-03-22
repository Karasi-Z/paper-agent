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

This module exposes the main package-level objects for Paper Agent.
"""


import os

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

from paper_agent.config import AppConfig
from paper_agent.client import PaperAgentClient
from paper_agent.workflow.service import PaperAgentService

__all__ = ["AppConfig", "PaperAgentClient", "PaperAgentService"]


###################################################################################################
###################################################################################################
### End of file
