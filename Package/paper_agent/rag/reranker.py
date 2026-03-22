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

This module implements the reranker abstraction for Paper Agent.
"""


from paper_agent.utils.text_cleaner import expand_query_for_retrieval, tokenize


class KeywordReranker:
    """
    KeywordReranker
    ---------------
    Lightweight lexical reranker for retrieved evidence.
    """

    def rerank(self, ranked_item_list: list[dict], query: str = "") -> list[dict]:
        """
        Function Function:

            Re-rank items with lexical overlap and section prior.
        """

        query_token_set = set(tokenize(expand_query_for_retrieval(query)))
        rescored_item_list: list[dict] = []
        for item in ranked_item_list:
            section_title = str(item.get("metadata", {}).get("section_title", "")).lower()
            document_token_set = set(tokenize(item.get("document", "")))
            overlap_score = 0.0
            if query_token_set:
                overlap_score = len(query_token_set & document_token_set) / len(query_token_set)

            section_bonus = 0.0
            if section_title in {"abstract", "introduction", "conclusion"}:
                section_bonus = 0.03
            elif section_title.startswith("method"):
                section_bonus = 0.02

            updated_item = dict(item)
            updated_item["score"] = float(item.get("score", 0.0)) + 0.2 * overlap_score + section_bonus
            rescored_item_list.append(updated_item)

        rescored_item_list.sort(key=lambda item: item["score"], reverse=True)
        return rescored_item_list


class PassThroughReranker(KeywordReranker):
    """
    PassThroughReranker
    -------------------
    Backward-compatible alias of the lightweight reranker.
    """


###################################################################################################
###################################################################################################
### End of file
