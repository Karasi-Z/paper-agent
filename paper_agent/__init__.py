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

This module provides the repository-root compatibility package for
Paper Agent so that `python -m paper_agent` and direct imports work
without editable installation.
"""


import os
import sys
from pathlib import Path
from pkgutil import extend_path


os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

__path__ = extend_path(__path__, __name__)
root_dir = Path(__file__).resolve().parent.parent
vendor_dir = root_dir / ".vendor"
package_dir = root_dir / "Package" / "paper_agent"
if vendor_dir.exists():
    vendor_text = str(vendor_dir)
    if vendor_text not in sys.path:
        sys.path.insert(0, vendor_text)
if package_dir.exists():
    __path__.append(str(package_dir))

from paper_agent.client import PaperAgentClient  # noqa: E402
from paper_agent.config import AppConfig  # noqa: E402
from paper_agent.workflow.service import PaperAgentService  # noqa: E402

__all__ = ["AppConfig", "PaperAgentClient", "PaperAgentService"]


###################################################################################################
###################################################################################################
### End of file
