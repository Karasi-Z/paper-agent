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

This module implements parser backend selection for Paper Agent.
"""


from pathlib import Path

from paper_agent.models.entities import DocumentParseResult
from paper_agent.parsing.adapters import BasicParserAdapter, DoclingParserAdapter, GrobidParserAdapter


class ParserService:
    """
    ParserService
    -------------
    Parser backend orchestration service.
    """

    def __init__(self, backend: str = "auto", grobid_url: str = "http://127.0.0.1:8070") -> None:
        """
        Function Function:

            Initialize parser service.
        """

        self.backend = backend
        self.grobid_url = grobid_url
        self.basic_adapter = BasicParserAdapter()

    def parse_file(self, path: str | Path, fallback_title: str | None = None) -> DocumentParseResult:
        """
        Function Function:

            Parse file with configured backend and fallback.
        """

        if self.backend == "docling":
            return self._parse_with_docling(path, fallback_title)
        if self.backend == "grobid":
            return self._parse_with_grobid(path, fallback_title)
        if self.backend == "auto":
            if str(path).lower().endswith(".pdf"):
                try:
                    return self._parse_with_docling(path, fallback_title)
                except Exception:
                    try:
                        return self._parse_with_grobid(path, fallback_title)
                    except Exception:
                        return self.basic_adapter.parse_file(path, fallback_title)
            return self.basic_adapter.parse_file(path, fallback_title)
        return self.basic_adapter.parse_file(path, fallback_title)

    def parse_text(self, text: str, title: str) -> DocumentParseResult:
        """
        Function Function:

            Parse raw text with basic backend.
        """

        return self.basic_adapter.document_parser.parse_text(text, title)

    def _parse_with_docling(self, path: str | Path, fallback_title: str | None = None) -> DocumentParseResult:
        """
        Function Function:

            Parse file with Docling adapter.
        """

        adapter = DoclingParserAdapter()
        return adapter.parse_file(path, fallback_title)

    def _parse_with_grobid(self, path: str | Path, fallback_title: str | None = None) -> DocumentParseResult:
        """
        Function Function:

            Parse file with GROBID adapter.
        """

        adapter = GrobidParserAdapter(grobid_url=self.grobid_url)
        return adapter.parse_file(path, fallback_title)


###################################################################################################
###################################################################################################
### End of file
