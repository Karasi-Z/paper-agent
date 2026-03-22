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

This module implements the literature synchronization agent for Paper Agent.
"""


from pathlib import Path

from paper_agent.literature.manager import build_literature_manager
from paper_agent.models.entities import Paper
from paper_agent.parsing.service import ParserService


class LibrarySyncAgent:
    """
    LibrarySyncAgent
    ----------------
    Literature manager synchronization agent.
    """

    def __init__(self, notes_dir: str, parser_service: ParserService) -> None:
        """
        Function Function:

            Initialize library synchronization agent.
        """

        self.notes_dir = notes_dir
        self.parser_service = parser_service

    def sync(
        self,
        provider: str,
        library_path: str,
        collection_id: str | None = None,
        library_options: dict | None = None,
    ) -> list[Paper]:
        """
        Function Function:

            Sync items from literature manager export.
        """

        manager = build_literature_manager(
            provider=provider,
            library_path=library_path,
            notes_dir=self.notes_dir,
            options=library_options,
        )
        paper_list: list[Paper] = []
        for item in manager.pull_items(collection_id=collection_id):
            content_text = ""
            abstract = item.abstract
            attachment_path = item.attachment_path
            if attachment_path is None:
                attachment_path = manager.pull_pdf(item.item_id)
            if attachment_path and Path(attachment_path).exists():
                parse_result = self.parser_service.parse_file(attachment_path, fallback_title=item.title)
                content_text = parse_result.full_text
                abstract = item.abstract or parse_result.abstract

            paper_list.append(
                Paper(
                    source=provider,
                    source_key=item.item_id,
                    title=item.title,
                    authors=item.authors,
                    abstract=abstract,
                    tags=item.tags,
                    pdf_path=attachment_path,
                    metadata=item.metadata,
                    content_text=content_text,
                )
            )
        return paper_list

    def push_note(
        self,
        provider: str,
        library_path: str,
        item_id: str,
        note_md: str,
        library_options: dict | None = None,
    ) -> dict[str, str | None]:
        """
        Function Function:

            Push note to literature manager backend.
        """

        manager = build_literature_manager(
            provider=provider,
            library_path=library_path,
            notes_dir=self.notes_dir,
            options=library_options,
        )
        return manager.push_note(item_id=item_id, note_md=note_md)


###################################################################################################
###################################################################################################
### End of file
