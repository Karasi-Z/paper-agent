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

This module implements the parse agent for Paper Agent.
"""


from pathlib import Path

from paper_agent.models.entities import DocumentParseResult, Paper
from paper_agent.parsing.service import ParserService


class ParseAgent:
    """
    ParseAgent
    ----------
    Local document parsing agent.
    """

    def __init__(self, parser_service: ParserService) -> None:
        """
        Function Function:

            Initialize parse agent.
        """

        self.parser_service = parser_service

    def parse_paper(self, paper: Paper) -> DocumentParseResult:
        """
        Function Function:

            Parse paper from local content or attachment.
        """

        if paper.content_text.strip():
            return self.parser_service.parse_text(paper.content_text, title=paper.title)

        if paper.pdf_path and Path(paper.pdf_path).exists():
            return self.parser_service.parse_file(paper.pdf_path, fallback_title=paper.title)

        fallback_text = "\n\n".join(part for part in [paper.title, paper.abstract] if part).strip()
        return self.parser_service.parse_text(fallback_text, title=paper.title)


###################################################################################################
###################################################################################################
### End of file
