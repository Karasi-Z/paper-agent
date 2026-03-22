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

This module prepares local import paths for workspace execution.
"""


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
for candidate in (ROOT / ".vendor", ROOT / "Package"):
    candidate_text = str(candidate)
    if candidate.exists() and candidate_text not in sys.path:
        sys.path.insert(0, candidate_text)


###################################################################################################
###################################################################################################
### End of file
