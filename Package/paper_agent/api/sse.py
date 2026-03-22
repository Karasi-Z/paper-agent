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

This module implements SSE helpers for Paper Agent.
"""


import json

from paper_agent.models.entities import RunEvent


def build_run_event_stream(run_event_list: list[RunEvent]):
    """
    Function Function:

        Build SSE event stream for persisted workflow events.
    """

    for item in run_event_list:
        payload = json.dumps(item.model_dump(mode="json"), ensure_ascii=False)
        yield f"event: {item.event_name}\ndata: {payload}\n\n"


###################################################################################################
###################################################################################################
### End of file
