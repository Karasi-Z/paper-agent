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

This module implements the chunking service for Paper Agent.
"""


import re

from paper_agent.models.entities import DocumentParseResult, PaperChunk
from paper_agent.utils.text_cleaner import chunk_words


class ChunkingService:
    """
    ChunkingService
    ---------------
    Document chunking service.
    """

    def chunk_document(
        self,
        parse_result: DocumentParseResult,
        paper_id: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[PaperChunk]:
        """
        Function Function:

            Convert parsed document into overlapping retrieval chunks.
        """

        chunk_list: list[PaperChunk] = []
        source_section_list = parse_result.sections or [{"title": "body", "content": parse_result.full_text}]
        chunk_index = 0

        for section in source_section_list:
            for chunk_text in chunk_words(section["content"], size=chunk_size, overlap=chunk_overlap):
                chunk_list.append(
                    PaperChunk(
                        paper_id=paper_id,
                        section_title=section["title"],
                        chunk_index=chunk_index,
                        content=chunk_text,
                        token_count=len(chunk_text.split()),
                        citation_markers=re.findall(r"\[[0-9,\- ]+\]", chunk_text),
                    )
                )
                chunk_index += 1

        if not chunk_list and parse_result.full_text:
            chunk_list.append(
                PaperChunk(
                    paper_id=paper_id,
                    section_title="body",
                    chunk_index=0,
                    content=parse_result.full_text,
                    token_count=len(parse_result.full_text.split()),
                )
            )
        return chunk_list


###################################################################################################
###################################################################################################
### End of file
