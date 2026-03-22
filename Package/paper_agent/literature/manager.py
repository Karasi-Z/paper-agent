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

This module implements the literature manager interface and local adapters
for Zotero, Mendeley, and EndNote style JSON exports.
"""


import json
from pathlib import Path
from typing import Protocol

from paper_agent.models.entities import LibraryItem
from paper_agent.literature.zotero_web_api import ZoteroWebApiManager
from paper_agent.utils.file_utils import write_text_file


class LiteratureManager(Protocol):
    """
    LiteratureManager
    -----------------
    Unified literature manager protocol.
    """

    provider: str

    def connect(self, **kwargs: str) -> None: ...
    def search_paper(self, query: str, limit: int = 20) -> list[LibraryItem]: ...
    def pull_items(self, collection_id: str | None = None) -> list[LibraryItem]: ...
    def pull_pdf(self, item_id: str) -> str | None: ...
    def push_note(self, item_id: str, note_md: str) -> dict[str, str | None]: ...
    def export_metadata(self, item_ids: list[str], fmt: str = "bibtex") -> str: ...


class JsonLibraryManager:
    """
    JsonLibraryManager
    ------------------
    Local JSON export based literature manager.
    """

    provider = "library"

    def __init__(self, library_path: str | Path, notes_dir: str | Path) -> None:
        """
        Function Function:

            Initialize JSON library manager.
        """

        self.library_path = Path(library_path)
        self.notes_dir = Path(notes_dir)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.item_list: list[LibraryItem] = []

    def connect(self, **kwargs: str) -> None:
        """
        Function Function:

            Load JSON export content.
        """

        if not self.library_path.exists():
            raise FileNotFoundError(self.library_path)

        payload = json.loads(self.library_path.read_text(encoding="utf-8"))
        raw_item_list = payload if isinstance(payload, list) else payload.get("items", [])
        self.item_list = [self._to_item(item) for item in raw_item_list]

    def search_paper(self, query: str, limit: int = 20) -> list[LibraryItem]:
        """
        Function Function:

            Search items by simple lexical overlap.
        """

        query_token_set = {token.lower() for token in query.split()}
        ranked_list: list[tuple[int, LibraryItem]] = []
        for item in self.item_list:
            haystack = f"{item.title} {item.abstract}".lower()
            ranked_list.append((sum(token in haystack for token in query_token_set), item))
        ranked_list.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in ranked_list[:limit]]

    def pull_items(self, collection_id: str | None = None) -> list[LibraryItem]:
        """
        Function Function:

            Pull literature items optionally by collection.
        """

        if collection_id is None:
            return list(self.item_list)
        return [item for item in self.item_list if item.metadata.get("collection_id") == collection_id]

    def pull_pdf(self, item_id: str) -> str | None:
        """
        Function Function:

            Get local attachment path for one item.
        """

        item = next((item for item in self.item_list if item.item_id == item_id), None)
        return item.attachment_path if item else None

    def push_note(self, item_id: str, note_md: str) -> dict[str, str | None]:
        """
        Function Function:

            Write generated note to local notes directory.
        """

        note_path = write_text_file(self.notes_dir / f"{self.provider}_{item_id}.md", note_md)
        return {
            "note_ref": str(note_path),
            "backup_path": str(note_path),
        }

    def export_metadata(self, item_ids: list[str], fmt: str = "bibtex") -> str:
        """
        Function Function:

            Export metadata in BibTeX or JSON format.
        """

        selected_item_list = [item for item in self.item_list if item.item_id in item_ids]
        if fmt.lower() != "bibtex":
            return json.dumps([item.model_dump(mode="json") for item in selected_item_list], ensure_ascii=False, indent=2)

        block_list: list[str] = []
        for item in selected_item_list:
            author_text = " and ".join(item.authors) if item.authors else "Unknown"
            key = item.item_id.replace(" ", "_")
            block_list.append(
                f"@article{{{key},\n"
                f"  title = {{{item.title}}},\n"
                f"  author = {{{author_text}}},\n"
                f"  abstract = {{{item.abstract}}}\n"
                f"}}"
            )
        return "\n\n".join(block_list)

    def _to_item(self, raw: dict) -> LibraryItem:
        """
        Function Function:

            Convert raw JSON object to unified library item.
        """

        attachment_path = raw.get("attachment_path")
        if attachment_path:
            attachment_path = str(Path(attachment_path).expanduser())

        return LibraryItem(
            item_id=str(raw.get("item_id") or raw.get("key") or raw.get("id")),
            title=raw.get("title") or "Untitled",
            authors=raw.get("authors") or [item.get("name", "") for item in raw.get("creators", []) if item.get("name")],
            abstract=raw.get("abstract") or raw.get("abstractNote") or "",
            tags=raw.get("tags") or [item.get("tag", "") for item in raw.get("tags", []) if isinstance(item, dict)],
            attachment_path=attachment_path,
            metadata=raw,
        )


class ZoteroManager(JsonLibraryManager):
    """
    ZoteroManager
    -------------
    Local Zotero export adapter.
    """

    provider = "zotero"


class MendeleyManager(JsonLibraryManager):
    """
    MendeleyManager
    ---------------
    Local Mendeley export adapter.
    """

    provider = "mendeley"


class EndNoteManager(JsonLibraryManager):
    """
    EndNoteManager
    --------------
    Local EndNote export adapter.
    """

    provider = "endnote"


def build_literature_manager(
    provider: str,
    library_path: str | Path,
    notes_dir: str | Path,
    options: dict | None = None,
) -> LiteratureManager:
    """
    Function Function:

        Build literature manager from provider name.
    """

    options = options or {}
    if provider == "zotero" and options.get("mode") == "web_api":
        manager = ZoteroWebApiManager(
            notes_dir=notes_dir,
            library_type=options.get("library_type", "users"),
            library_id=str(options.get("library_id", "")),
            api_key=options.get("api_key"),
            base_url=options.get("base_url", "https://api.zotero.org"),
        )
        manager.connect()
        return manager

    provider_map = {
        "zotero": ZoteroManager,
        "mendeley": MendeleyManager,
        "endnote": EndNoteManager,
    }
    if provider not in provider_map:
        raise ValueError(f"Unsupported provider: {provider}")

    manager = provider_map[provider](library_path=library_path, notes_dir=notes_dir)
    manager.connect()
    return manager


###################################################################################################
###################################################################################################
### End of file
