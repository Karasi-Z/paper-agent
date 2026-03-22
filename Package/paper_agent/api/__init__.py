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

This module exposes API components for Paper Agent.
"""

def create_app(config=None):
    """
    Function Function:

        Lazily expose FastAPI application factory.
    """

    from paper_agent.server import create_app as app_factory

    return app_factory(config)


__all__ = ["create_app"]


###################################################################################################
###################################################################################################
### End of file
