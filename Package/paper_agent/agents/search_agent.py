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

This module implements the search agent for Paper Agent.
"""


from paper_agent.models.entities import Paper
from paper_agent.retrieval.arxiv_client import ArxivClient


class SearchAgent:
    """
    SearchAgent
    -----------
    Research paper search agent.
    """

    def __init__(self, arxiv_client: ArxivClient) -> None:
        """
        Function Function:

            Initialize search agent.
        """

        self.arxiv_client = arxiv_client

    def search(
        self,
        query: str,
        limit: int,
        author: str | None = None,
        categories: list[str] | None = None,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> list[Paper]:
        """
        Function Function:

            Search candidate papers.
        """

        return self.arxiv_client.search(
            query=query,
            limit=limit,
            author=author,
            categories=categories or [],
            from_year=from_year,
            to_year=to_year,
        )


###################################################################################################
###################################################################################################
### End of file
