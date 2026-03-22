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

This module implements dependency providers for FastAPI.
"""


from fastapi import Request

from paper_agent.config import AppConfig
from paper_agent.workflow.service import PaperAgentService


def get_service(request: Request) -> PaperAgentService:
    """
    Function Function:

        Return FastAPI-bound application service.
    """

    service = getattr(request.app.state, "service", None)
    if service is not None:
        return service
    return PaperAgentService(AppConfig.from_env())


###################################################################################################
###################################################################################################
### End of file
