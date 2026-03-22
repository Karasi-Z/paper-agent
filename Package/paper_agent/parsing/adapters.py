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

This module implements parser backend adapters for Paper Agent.

Description of Class and Function
--------------------------------
(1) BaseParserAdapter
    - Abstract parser adapter

(2) BasicParserAdapter
    - Local lightweight parser adapter

(3) DoclingParserAdapter
    - Docling-based parser adapter

(4) GrobidParserAdapter
    - GROBID REST parser adapter
"""


from abc import ABC, abstractmethod
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

from paper_agent.models.entities import DocumentParseResult
from paper_agent.utils.pdf_parser import BasicDocumentParser
from paper_agent.utils.text_cleaner import normalize_whitespace


class BaseParserAdapter(ABC):
    """
    BaseParserAdapter
    -----------------
    Abstract parser adapter interface.
    """

    @abstractmethod
    def parse_file(self, path: str | Path, fallback_title: str | None = None) -> DocumentParseResult:
        """
        Function Function:

            Parse local file to structured document result.
        """


class BasicParserAdapter(BaseParserAdapter):
    """
    BasicParserAdapter
    ------------------
    Lightweight local parser adapter.
    """

    def __init__(self, document_parser: BasicDocumentParser | None = None) -> None:
        """
        Function Function:

            Initialize basic parser adapter.
        """

        self.document_parser = document_parser or BasicDocumentParser()

    def parse_file(self, path: str | Path, fallback_title: str | None = None) -> DocumentParseResult:
        """
        Function Function:

            Parse local file with basic parser.
        """

        return self.document_parser.parse_file(path=path, fallback_title=fallback_title)


class DoclingParserAdapter(BaseParserAdapter):
    """
    DoclingParserAdapter
    --------------------
    Docling-based parser adapter with local fallback expectations.
    """

    def parse_file(self, path: str | Path, fallback_title: str | None = None) -> DocumentParseResult:
        """
        Function Function:

            Parse local file with Docling.
        """

        from docling.document_converter import DocumentConverter

        source_path = str(path)
        converter = DocumentConverter()
        conversion_result = converter.convert(source_path)
        markdown_text = conversion_result.document.export_to_markdown()
        title = fallback_title or Path(path).stem
        abstract = ""
        for line in markdown_text.splitlines():
            stripped_line = line.strip().lstrip("#").strip()
            if stripped_line:
                title = stripped_line
                break
        section_list = self._markdown_to_sections(markdown_text)
        for item in section_list:
            if item["title"].lower() == "abstract":
                abstract = item["content"]
                break
        return DocumentParseResult(
            title=title,
            abstract=abstract,
            full_text=normalize_whitespace(markdown_text),
            sections=section_list or [{"title": "body", "content": normalize_whitespace(markdown_text)}],
        )

    def _markdown_to_sections(self, markdown_text: str) -> list[dict[str, str]]:
        """
        Function Function:

            Convert Docling markdown output into coarse sections.
        """

        section_list: list[dict[str, str]] = []
        current_title = "body"
        current_line_list: list[str] = []
        for line in markdown_text.splitlines():
            stripped_line = line.strip()
            if stripped_line.startswith("#"):
                if current_line_list:
                    section_list.append(
                        {
                            "title": current_title,
                            "content": normalize_whitespace("\n".join(current_line_list)),
                        }
                    )
                    current_line_list = []
                current_title = stripped_line.lstrip("#").strip() or "body"
                continue
            if stripped_line:
                current_line_list.append(stripped_line)

        if current_line_list:
            section_list.append(
                {
                    "title": current_title,
                    "content": normalize_whitespace("\n".join(current_line_list)),
                }
            )
        return [item for item in section_list if item["content"]]


class GrobidParserAdapter(BaseParserAdapter):
    """
    GrobidParserAdapter
    -------------------
    GROBID REST parser adapter.
    """

    def __init__(self, grobid_url: str) -> None:
        """
        Function Function:

            Initialize GROBID parser adapter.
        """

        self.grobid_url = grobid_url.rstrip("/")

    def parse_file(self, path: str | Path, fallback_title: str | None = None) -> DocumentParseResult:
        """
        Function Function:

            Parse local PDF through GROBID REST service.
        """

        file_path = Path(path)
        endpoint = f"{self.grobid_url}/api/processFulltextDocument"
        with file_path.open("rb") as file_obj:
            response = requests.post(
                endpoint,
                files={"input": (file_path.name, file_obj, "application/pdf")},
                data={"consolidateHeader": "1", "segmentSentences": "1"},
                timeout=120,
            )
        response.raise_for_status()
        return self._parse_tei(response.text, fallback_title or file_path.stem)

    def _parse_tei(self, tei_xml: str, fallback_title: str) -> DocumentParseResult:
        """
        Function Function:

            Parse TEI XML response into unified document result.
        """

        root = ET.fromstring(tei_xml)
        namespace = {"tei": "http://www.tei-c.org/ns/1.0"}
        title = fallback_title
        title_element = root.find(".//tei:titleStmt/tei:title", namespace)
        if title_element is not None and title_element.text:
            title = normalize_whitespace(title_element.text)

        abstract_element = root.find(".//tei:profileDesc/tei:abstract", namespace)
        abstract = normalize_whitespace("".join(abstract_element.itertext())) if abstract_element is not None else ""

        body_element = root.find(".//tei:text/tei:body", namespace)
        body_text = normalize_whitespace("".join(body_element.itertext())) if body_element is not None else ""

        section_list: list[dict[str, str]] = []
        if body_element is not None:
            for div_element in body_element.findall(".//tei:div", namespace):
                head_element = div_element.find("./tei:head", namespace)
                section_title = normalize_whitespace(head_element.text) if head_element is not None and head_element.text else "body"
                section_text = normalize_whitespace("".join(div_element.itertext()))
                if section_text:
                    section_list.append({"title": section_title, "content": section_text})

        if not section_list and body_text:
            section_list.append({"title": "body", "content": body_text})

        return DocumentParseResult(
            title=title,
            abstract=abstract,
            full_text=body_text or abstract or title,
            sections=section_list,
        )


###################################################################################################
###################################################################################################
### End of file
