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

This module implements logging configuration for Paper Agent.
"""


import logging


def setup_logging(level: int = logging.INFO) -> None:
    """
    Function Function:

        Configure root logging for local execution.
    """

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


###################################################################################################
###################################################################################################
### End of file
