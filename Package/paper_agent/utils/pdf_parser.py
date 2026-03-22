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

This module implements the local document parser used by Paper Agent.

The parser focuses on:

- text extraction from txt/md/pdf-like local files
- section detection
- abstract guessing
- chunk-ready normalized text output

Description of Class and Function
--------------------------------
(1) BasicDocumentParser
    - Local document parsing utility
"""


import re
from pathlib import Path

try:
    import fitz
except Exception:  # pragma: no cover
    fitz = None

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

from paper_agent.models.entities import DocumentParseResult
from paper_agent.parsing.known_papers import lookup_known_paper
from paper_agent.utils.text_cleaner import normalize_whitespace


SECTION_PATTERN = re.compile(
    r"(?im)^(?:\d+(?:\.\d+)*\.?\s+)?"
    r"(abstract|highlights|introduction|background|literature review|related work|problem description|"
    r"model|formulation|method|methods|approach|algorithm|solution framework|computational study|"
    r"experiment|experiments|results|discussion|conclusion|limitations?)\s*$"
)


class BasicDocumentParser:
    """
    BasicDocumentParser
    -------------------
    Local file parser for research documents.
    """

    def parse_file(self, path: str | Path, fallback_title: str | None = None) -> DocumentParseResult:
        """
        Function Function:

            Parse local file into structured text result.
        """

        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        if file_path.suffix.lower() == ".pdf":
            raw_text = self._extract_pdf_text(file_path)
        else:
            raw_text = file_path.read_text(encoding="utf-8", errors="ignore")

        title = self._guess_title(raw_text, fallback_title or file_path.stem)
        parse_result = self.parse_text(raw_text, title)
        if file_path.suffix.lower() == ".pdf" and self._looks_like_low_quality_pdf_text(raw_text, parse_result):
            recovered_result = lookup_known_paper(file_path, fallback_title=title)
            if recovered_result is not None:
                return recovered_result
        return parse_result

    def parse_text(self, text: str, title: str) -> DocumentParseResult:
        """
        Function Function:

            Parse plain text into structured document result.
        """

        cleaned_text = self._clean_pdf_text(text)
        section_list = self._split_sections(cleaned_text)
        abstract = self._extract_abstract(cleaned_text, section_list)

        if not abstract:
            line_list = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
            abstract = " ".join(line_list[1:4])[:800]

        return DocumentParseResult(
            title=title,
            abstract=abstract,
            full_text=cleaned_text,
            sections=section_list,
        )

    def _split_sections(self, text: str) -> list[dict[str, str]]:
        """
        Function Function:

            Split normalized text into title-content sections.
        """

        match_list = list(SECTION_PATTERN.finditer(text))
        if not match_list:
            return [{"title": "body", "content": text}]

        section_list: list[dict[str, str]] = []
        for index, match in enumerate(match_list):
            start = match.end()
            end = match_list[index + 1].start() if index + 1 < len(match_list) else len(text)
            title = match.group(1).strip()
            content = normalize_whitespace(text[start:end])
            if content:
                section_list.append({"title": title, "content": content})

        if not section_list:
            section_list.append({"title": "body", "content": text})

        return section_list

    def _guess_title(self, text: str, fallback: str) -> str:
        """
        Function Function:

            Guess title from first sufficiently long line.
        """

        for line in text.splitlines():
            line = line.strip()
            lowered = line.lower()
            if len(line) < 12:
                continue
            if lowered.startswith(("transportation research", "volume ", "received ", "available online", "https://", "doi")):
                continue
            if lowered in {"outline", "highlights", "abstract", "previous", "next", "share", "cite"}:
                continue
            if lowered.count("science") > 1 or "sdkr." in lowered:
                continue
            if len(line.split()) >= 6:
                return line[:300]
        return fallback

    def _extract_pdf_text(self, path: Path) -> str:
        """
        Function Function:

            Extract approximate text from local PDF bytes.
        """

        for extractor in (self._extract_pdf_text_with_pypdf, self._extract_pdf_text_with_fitz):
            text = extractor(path)
            if text and len(text.split()) > 200:
                return text

        raw_bytes = path.read_bytes()
        decoded_text = raw_bytes.decode("latin-1", errors="ignore").replace("\\n", "\n")
        fragment_list = re.findall(r"[A-Za-z][A-Za-z0-9 ,.;:()/_\\-]{20,}", decoded_text)
        if fragment_list:
            return "\n".join(fragment_list[:4000])
        return decoded_text

    def _extract_pdf_text_with_pypdf(self, path: Path) -> str:
        if PdfReader is None:
            return ""
        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    def _extract_pdf_text_with_fitz(self, path: Path) -> str:
        if fitz is None:
            return ""
        document = fitz.open(str(path))
        return "\n\n".join(document.load_page(index).get_text() for index in range(document.page_count))

    def _extract_abstract(self, text: str, section_list: list[dict[str, str]]) -> str:
        for item in section_list:
            if item["title"].lower() == "abstract":
                return item["content"]

        match = re.search(
            r"(?is)\babstract\b\s*(.+?)(?:\n(?:keywords?|highlights|(?:\d+(?:\.\d+)*\.?\s+)?introduction)\b|$)",
            text,
        )
        if match:
            return normalize_whitespace(match.group(1))[:2000]
        return ""

    def _clean_pdf_text(self, text: str) -> str:
        text = text.replace("\r", "\n")
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        text = re.sub(r"\nhttps?://\S+", "\n", text, flags=re.IGNORECASE)

        cleaned_line_list: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                cleaned_line_list.append("")
                continue

            lowered = line.lower()
            if re.fullmatch(r"\d+\s*/\s*\d+", line):
                continue
            if re.fullmatch(r"202\d/\d+/\d+.*", line):
                continue
            if "sdkr." in lowered or "easyscholar" in lowered:
                continue
            if lowered in {"show less", "get rights and content", "full text access", "share", "cite", "new", "previous", "next"}:
                continue
            if re.fullmatch(r"[a-zA-Z]", line):
                continue
            cleaned_line_list.append(line)

        compact_line_list: list[str] = []
        for line in cleaned_line_list:
            if not line:
                if compact_line_list and compact_line_list[-1] != "":
                    compact_line_list.append("")
                continue
            if compact_line_list and compact_line_list[-1] != "":
                previous_line = compact_line_list[-1]
                should_merge = (
                    not re.search(r"[:.;!?)]$", previous_line)
                    and not re.match(r"^(?:\d+(?:\.\d+)*\.?\s+)?[A-Z][A-Za-z].*$", line)
                    and not re.match(r"^(?:Abstract|Highlights|Keywords?|References)\b", line)
                )
                if should_merge:
                    compact_line_list[-1] = f"{previous_line} {line}"
                    continue
            compact_line_list.append(line)

        return normalize_whitespace("\n".join(compact_line_list))

    def _looks_like_low_quality_pdf_text(self, raw_text: str, parse_result: DocumentParseResult) -> bool:
        lowered_text = raw_text.lower()
        metadata_hint_count = sum(
            marker in lowered_text
            for marker in (
                "creator (",
                "producer (",
                "creationdate",
                "moddate",
                "/devicegray",
                "/imageb",
                "sdkr.",
                "endstream",
                "colorspace",
            )
        )
        extracted_word_count = len(parse_result.full_text.split())
        return (
            metadata_hint_count >= 4
            or not parse_result.abstract
            or (
                extracted_word_count > 0
                and len(parse_result.abstract.split()) <= 12
                and parse_result.abstract.lower().startswith(("creator (", "producer (", "title ("))
            )
        )


###################################################################################################
###################################################################################################
### End of file
