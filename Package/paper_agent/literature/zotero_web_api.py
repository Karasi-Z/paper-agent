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

This module implements a read-write Zotero Web API manager for
Paper Agent.

The implementation follows Zotero Web API v3 endpoints:

- `https://api.zotero.org/users/<userID>/items`
- `https://api.zotero.org/groups/<groupID>/items`
- `.../collections/<collectionKey>/items`
- `.../items/<itemKey>/file`
- `.../items` (write note item)

References
----------
- https://www.zotero.org/support/dev/web_api/v3/basics
- https://www.zotero.org/support/dev/web_api/v3/start
"""

import html
import json
from pathlib import Path
from uuid import uuid4

import requests

from paper_agent.models.entities import LibraryItem
from paper_agent.utils.file_utils import write_text_file


class ZoteroWebApiManager:
    """
    ZoteroWebApiManager
    -------------------
    Read-write Zotero Web API manager.
    """

    provider = "zotero"

    def __init__(
        self,
        notes_dir: str | Path,
        library_type: str,
        library_id: str,
        api_key: str | None = None,
        base_url: str = "https://api.zotero.org",
    ) -> None:
        """
        Function Function:

            Initialize Zotero Web API manager.
        """

        self.notes_dir = Path(notes_dir)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.library_type = library_type
        self.library_id = library_id
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.item_list: list[LibraryItem] = []

    def connect(self, **kwargs: str) -> None:
        """
        Function Function:

            Validate configuration and initialize manager.
        """

        if self.library_type not in {"users", "groups"}:
            raise ValueError("library_type must be 'users' or 'groups'")

    def search_paper(self, query: str, limit: int = 20) -> list[LibraryItem]:
        """
        Function Function:

            Search library items using Zotero quick search.
        """

        response = requests.get(
            self._items_url(),
            headers=self._headers(),
            params={"q": query, "limit": limit, "format": "json"},
            timeout=30,
        )
        response.raise_for_status()
        self.item_list = [self._to_item(item) for item in response.json()]
        return list(self.item_list)

    def pull_items(self, collection_id: str | None = None) -> list[LibraryItem]:
        """
        Function Function:

            Pull items from Zotero Web API.
        """

        raw_item_list = self._pull_paged_items(collection_id=collection_id)
        self.item_list = [self._to_item(item) for item in raw_item_list if self._is_literature_item(item)]
        return list(self.item_list)

    def pull_pdf(self, item_id: str) -> str | None:
        """
        Function Function:

            Download Zotero attachment file when accessible.
        """

        response = requests.get(
            f"{self._library_prefix()}/items/{item_id}/file",
            headers=self._headers(),
            timeout=60,
        )
        if response.status_code >= 400:
            return None
        content_disposition = response.headers.get("Content-Disposition", "")
        filename = self._guess_filename(content_disposition, fallback=f"{item_id}.pdf")
        file_path = self.notes_dir / filename
        file_path.write_bytes(response.content)
        return str(file_path)

    def push_note(self, item_id: str, note_md: str) -> dict[str, str | None]:
        """
        Function Function:

            Push note to Zotero and persist local backup.
        """

        note_path = write_text_file(self.notes_dir / f"zotero_api_{item_id}.md", note_md)
        response = requests.post(
            self._items_url(),
            headers=self._headers(is_write=True),
            json=[
                {
                    "itemType": "note",
                    "parentItem": item_id,
                    "note": self._markdown_to_note_html(note_md),
                }
            ],
            timeout=30,
        )
        response.raise_for_status()

        payload = response.json() if getattr(response, "text", "") else {}
        successful_map = payload.get("successful", {})
        first_success = next(iter(successful_map.values()), {}) if successful_map else {}
        note_key = first_success.get("key")
        if note_key is None and isinstance(first_success.get("data"), dict):
            note_key = first_success["data"].get("key")
        return {
            "note_ref": note_key or str(note_path),
            "backup_path": str(note_path),
        }

    def export_metadata(self, item_ids: list[str], fmt: str = "bibtex") -> str:
        """
        Function Function:

            Export selected metadata in JSON or BibTeX.
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

    def _headers(self, is_write: bool = False) -> dict[str, str]:
        """
        Function Function:

            Build request headers for Zotero API.
        """

        header_map = {"Zotero-API-Version": "3"}
        if self.api_key:
            header_map["Zotero-API-Key"] = self.api_key
        if is_write:
            if not self.api_key:
                raise ValueError("api_key is required for Zotero Web API write requests")
            header_map["Content-Type"] = "application/json"
            header_map["Zotero-Write-Token"] = uuid4().hex
        return header_map

    def _library_prefix(self) -> str:
        """
        Function Function:

            Build library URL prefix.
        """

        return f"{self.base_url}/{self.library_type}/{self.library_id}"

    def _items_url(self, collection_id: str | None = None) -> str:
        """
        Function Function:

            Build items endpoint URL.
        """

        if collection_id:
            return f"{self._library_prefix()}/collections/{collection_id}/items"
        return f"{self._library_prefix()}/items"

    def _pull_paged_items(self, collection_id: str | None = None) -> list[dict]:
        """
        Function Function:

            Pull all paged Zotero items for one library scope.
        """

        url = self._items_url(collection_id=collection_id)
        start = 0
        limit = 100
        raw_item_list: list[dict] = []
        while True:
            response = requests.get(
                url,
                headers=self._headers(),
                params={"start": start, "limit": limit, "format": "json"},
                timeout=30,
            )
            response.raise_for_status()
            batch_list = response.json()
            if not batch_list:
                break
            raw_item_list.extend(batch_list)
            if len(batch_list) < limit:
                break
            start += limit
        return raw_item_list

    def _is_literature_item(self, raw: dict) -> bool:
        """
        Function Function:

            Filter out Zotero note and attachment items.
        """

        data = raw.get("data", raw)
        item_type = str(data.get("itemType", "")).lower()
        return item_type not in {"attachment", "note", "annotation"}

    def _guess_filename(self, content_disposition: str, fallback: str) -> str:
        """
        Function Function:

            Guess attachment filename from HTTP header.
        """

        if "filename=" in content_disposition:
            return content_disposition.split("filename=", 1)[1].strip().strip('"')
        return fallback

    def _markdown_to_note_html(self, note_md: str) -> str:
        """
        Function Function:

            Convert Markdown-style note text to Zotero HTML.
        """

        block_list = [block.strip() for block in note_md.replace("\r\n", "\n").split("\n\n") if block.strip()]
        html_block_list: list[str] = []
        for block in block_list:
            line_list = [line.rstrip() for line in block.splitlines() if line.strip()]
            if not line_list:
                continue

            if all(line.lstrip().startswith("- ") for line in line_list):
                html_block_list.append(
                    "<ul>"
                    + "".join(f"<li>{html.escape(line.lstrip()[2:].strip())}</li>" for line in line_list)
                    + "</ul>"
                )
                continue

            first_line = line_list[0].lstrip()
            if first_line.startswith("#"):
                level = len(first_line) - len(first_line.lstrip("#"))
                level = min(max(level, 1), 6)
                title_text = first_line[level:].strip()
                html_block_list.append(f"<h{level}>{html.escape(title_text)}</h{level}>")
                if len(line_list) > 1:
                    paragraph = "<br />".join(html.escape(line) for line in line_list[1:])
                    html_block_list.append(f"<p>{paragraph}</p>")
                continue

            paragraph = "<br />".join(html.escape(line) for line in line_list)
            html_block_list.append(f"<p>{paragraph}</p>")

        return "\n".join(html_block_list)

    def _to_item(self, raw: dict) -> LibraryItem:
        """
        Function Function:

            Convert Zotero API item JSON to unified library item.
        """

        data = raw.get("data", raw)
        creator_list = data.get("creators", [])
        author_list = []
        for item in creator_list:
            if item.get("name"):
                author_list.append(item["name"])
            else:
                first_name = item.get("firstName", "")
                last_name = item.get("lastName", "")
                author_list.append(f"{first_name} {last_name}".strip())
        return LibraryItem(
            item_id=str(data.get("key") or data.get("itemKey") or data.get("id")),
            title=data.get("title") or "Untitled",
            authors=[item for item in author_list if item],
            abstract=data.get("abstractNote") or "",
            tags=[item.get("tag", "") for item in data.get("tags", []) if isinstance(item, dict)],
            attachment_path=None,
            metadata={"item_type": data.get("itemType"), **raw},
        )


###################################################################################################
###################################################################################################
### End of file
