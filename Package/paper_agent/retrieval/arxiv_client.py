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

This module implements the ArXiv retrieval client for Paper Agent.

Description of Class and Function
--------------------------------
(1) ArxivClient
    - ArXiv search client with remote and offline fallback modes
"""


from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from urllib.request import urlopen
import xml.etree.ElementTree as ET

from paper_agent.models.entities import Paper


OFFLINE_CATALOG: list[dict[str, Any]] = [
    {
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "authors": ["Patrick Lewis", "Ethan Perez"],
        "abstract": "This paper studies retrieval-augmented generation for knowledge-intensive tasks and factual generation.",
        "arxiv_id": "2005.11401",
        "categories": ["cs.CL", "cs.AI"],
        "year": 2020,
    },
    {
        "title": "PaperQA: Retrieval-Augmented Question Answering over Scientific Documents",
        "authors": ["Future House"],
        "abstract": "Citation-grounded scientific document question answering over local paper collections.",
        "arxiv_id": "offline-paperqa",
        "categories": ["cs.AI"],
        "year": 2024,
    },
    {
        "title": "Scientific Literature Clustering with Dense Text Embeddings",
        "authors": ["Example Author"],
        "abstract": "Dense embeddings support scientific paper clustering and topic survey generation.",
        "arxiv_id": "offline-cluster",
        "categories": ["cs.IR"],
        "year": 2023,
    },
    {
        "title": "Document Intelligence for PDFs with Structured Parsing",
        "authors": ["Example Parser Team"],
        "abstract": "Structured document parsing extracts sections, references, tables, and evidence anchors from research PDFs.",
        "arxiv_id": "offline-parser",
        "categories": ["cs.DL"],
        "year": 2023,
    },
]


class ArxivClient:
    """
    ArxivClient
    -----------
    ArXiv retrieval client with remote and offline modes.
    """

    base_url = "http://export.arxiv.org/api/query"

    def search(
        self,
        query: str,
        limit: int = 10,
        author: str | None = None,
        categories: list[str] | None = None,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> list[Paper]:
        """
        Function Function:

            Search ArXiv and fallback to offline catalog if needed.
        """

        try:
            return self._search_remote(query, limit, author, categories or [], from_year, to_year)
        except Exception:
            return self._search_offline(query, limit, author, categories or [], from_year, to_year)

    def _search_remote(
        self,
        query: str,
        limit: int,
        author: str | None,
        categories: list[str],
        from_year: int | None,
        to_year: int | None,
    ) -> list[Paper]:
        """
        Function Function:

            Search ArXiv remote API with metadata filters.
        """

        search_query = self._build_remote_query(
            query=query,
            author=author,
            categories=categories,
            from_year=from_year,
            to_year=to_year,
        )
        url = (
            f"{self.base_url}?search_query={quote(search_query)}&"
            f"start=0&max_results={limit}&sortBy=relevance&sortOrder=descending"
        )
        with urlopen(url, timeout=10) as response:
            payload = response.read()

        root = ET.fromstring(payload)
        namespace = {"atom": "http://www.w3.org/2005/Atom"}
        paper_list: list[Paper] = []
        for entry in root.findall("atom:entry", namespace):
            title = (entry.findtext("atom:title", default="", namespaces=namespace) or "").strip()
            if title.lower() == "arxiv query: search_query":
                continue

            abstract = (entry.findtext("atom:summary", default="", namespaces=namespace) or "").strip()
            author_list = [
                author_item.findtext("atom:name", default="", namespaces=namespace)
                for author_item in entry.findall("atom:author", namespace)
            ]
            category_list = [item.attrib.get("term", "") for item in entry.findall("atom:category", namespace)]
            paper_key = (entry.findtext("atom:id", default="", namespaces=namespace) or "").rsplit("/", 1)[-1]
            published_text = entry.findtext("atom:published", default="", namespaces=namespace)
            published_at = (
                datetime.fromisoformat(published_text.replace("Z", "+00:00"))
                if published_text
                else datetime.now(timezone.utc)
            )
            paper_list.append(
                Paper(
                    source="arxiv",
                    source_key=paper_key,
                    arxiv_id=paper_key,
                    title=title,
                    authors=[item for item in author_list if item],
                    abstract=abstract,
                    published_at=published_at,
                    metadata={
                        "query": query,
                        "author": author,
                        "categories": [item for item in category_list if item],
                    },
                )
            )
        return paper_list

    def _search_offline(
        self,
        query: str,
        limit: int,
        author: str | None,
        categories: list[str],
        from_year: int | None,
        to_year: int | None,
    ) -> list[Paper]:
        """
        Function Function:

            Search offline fallback catalog with basic metadata filtering.
        """

        query_term_set = {term.lower() for term in query.split() if term.strip()}
        normalized_category_set = {item.lower() for item in categories}
        ranked_list: list[tuple[int, dict[str, Any]]] = []
        for item in OFFLINE_CATALOG:
            if author and author.lower() not in " ".join(item["authors"]).lower():
                continue
            if normalized_category_set and not normalized_category_set.intersection({value.lower() for value in item["categories"]}):
                continue
            if from_year is not None and item["year"] < from_year:
                continue
            if to_year is not None and item["year"] > to_year:
                continue

            haystack = f"{item['title']} {item['abstract']} {' '.join(item['categories'])}".lower()
            score = sum(term in haystack for term in query_term_set)
            ranked_list.append((score, item))

        ranked_list.sort(key=lambda pair: pair[0], reverse=True)
        paper_list: list[Paper] = []
        for _, item in ranked_list[:limit]:
            paper_list.append(
                Paper(
                    source="arxiv",
                    source_key=item["arxiv_id"],
                    arxiv_id=item["arxiv_id"],
                    title=item["title"],
                    authors=item["authors"],
                    abstract=item["abstract"],
                    published_at=datetime(item["year"], 1, 1, tzinfo=timezone.utc),
                    metadata={"offline": True, "categories": item["categories"]},
                )
            )
        return paper_list

    def _build_remote_query(
        self,
        query: str,
        author: str | None,
        categories: list[str],
        from_year: int | None,
        to_year: int | None,
    ) -> str:
        """
        Function Function:

            Build ArXiv query expression with metadata filters.
        """

        part_list: list[str] = []
        if query.strip():
            part_list.append(f'all:"{query.strip()}"')
        if author:
            part_list.append(f'au:"{author.strip()}"')
        for item in categories:
            if item.strip():
                part_list.append(f'cat:{item.strip()}')
        if from_year is not None or to_year is not None:
            year_start = from_year if from_year is not None else 1990
            year_end = to_year if to_year is not None else datetime.now(timezone.utc).year
            part_list.append(f"submittedDate:[{year_start}01010000 TO {year_end}12312359]")
        return " AND ".join(part_list) if part_list else "all:paper"


###################################################################################################
###################################################################################################
### End of file
