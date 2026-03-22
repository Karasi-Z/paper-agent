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

This module implements the FastAPI application factory for Paper Agent.
"""


from functools import lru_cache

from fastapi import FastAPI

from paper_agent.api.routes import router
from paper_agent.config import AppConfig
from paper_agent.workflow.service import PaperAgentService


@lru_cache(maxsize=1)
def _default_service() -> PaperAgentService:
    """
    Function Function:

        Build cached default application service.
    """

    return PaperAgentService(AppConfig.from_env())


def create_app(config: AppConfig | None = None) -> FastAPI:
    """
    Function Function:

        Create FastAPI application.
    """

    app = FastAPI(title="Paper Agent", version="0.2.0")
    app.include_router(router)
    app.state.service = PaperAgentService(config) if config is not None else _default_service()
    return app


###################################################################################################
###################################################################################################
### End of file
