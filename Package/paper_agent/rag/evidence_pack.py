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

This module implements runtime evidence-pack construction for Paper Agent.

Description of Class and Function
--------------------------------
(1) EvidencePackBuilder
    - Build balanced evidence list with dedup and per-paper limits
"""


from collections import defaultdict

from paper_agent.models.entities import Evidence
from paper_agent.models.enums import EvidenceRole
from paper_agent.utils.text_cleaner import tokenize


SECTION_PRIOR_MAP = {
    "abstract": 0.08,
    "introduction": 0.06,
    "method": 0.05,
    "result": 0.06,
    "discussion": 0.04,
    "conclusion": 0.07,
}


class EvidencePackBuilder:
    """
    Build a diversity-aware evidence pack from ranked retrieval items.
    """

    def __init__(self, per_paper_limit: int = 2, max_items: int = 12) -> None:
        self.per_paper_limit = max(1, per_paper_limit)
        self.max_items = max(1, max_items)

    def build(self, query: str, ranked_item_list: list[dict], max_items: int | None = None) -> list[Evidence]:
        query_token_set = set(tokenize(query))
        candidate_list = [self._to_evidence(query_token_set, item) for item in ranked_item_list]
        candidate_list = self._deduplicate_chunks(candidate_list)
        candidate_list.sort(key=lambda item: item.final_score, reverse=True)
        return self._balanced_sample(candidate_list, max_items=max_items or self.max_items)

    def _to_evidence(self, query_token_set: set[str], ranked_item: dict) -> Evidence:
        metadata = dict(ranked_item.get("metadata") or {})
        section_title = str(metadata.get("section_title") or "body")
        quote = str(ranked_item.get("document") or "").strip()
        paper_id = str(metadata.get("paper_id") or "")
        paper_title = str(metadata.get("paper_title") or paper_id or "unknown")
        chunk_id = str(ranked_item.get("chunk_id") or "")

        retrieval_score = self._normalize_retrieval_score(ranked_item)
        rerank_score = float(ranked_item.get("score", retrieval_score))
        section_prior = self._section_prior(section_title)
        lexical_overlap = self._lexical_overlap(query_token_set, quote)
        final_score = 0.35 * retrieval_score + 0.45 * rerank_score + 0.1 * section_prior + 0.1 * lexical_overlap

        return Evidence(
            paper_id=paper_id,
            chunk_id=chunk_id,
            paper_title=paper_title,
            section_title=section_title,
            quote=quote,
            page_start=self._safe_int(metadata.get("page_start")),
            page_end=self._safe_int(metadata.get("page_end")),
            retrieval_score=round(retrieval_score, 6),
            rerank_score=round(rerank_score, 6),
            final_score=round(final_score, 6),
            role=self._infer_role(section_title, quote),
            reason=(
                f"selected_by=hybrid_rank;section={section_title or 'body'};"
                f"retrieval={retrieval_score:.4f};rerank={rerank_score:.4f};overlap={lexical_overlap:.4f}"
            ),
        )

    def _deduplicate_chunks(self, evidence_list: list[Evidence]) -> list[Evidence]:
        seen_chunk_id_set: set[str] = set()
        deduplicated_list: list[Evidence] = []
        for item in evidence_list:
            if not item.chunk_id or item.chunk_id in seen_chunk_id_set:
                continue
            seen_chunk_id_set.add(item.chunk_id)
            deduplicated_list.append(item)
        return deduplicated_list

    def _balanced_sample(self, evidence_list: list[Evidence], max_items: int) -> list[Evidence]:
        grouped_map: dict[str, list[Evidence]] = defaultdict(list)
        for item in evidence_list:
            grouped_map[item.paper_id].append(item)

        selected_list: list[Evidence] = []
        selected_per_paper_map: dict[str, int] = defaultdict(int)
        ordered_paper_id_list = sorted(grouped_map.keys(), key=lambda paper_id: grouped_map[paper_id][0].final_score, reverse=True)

        while len(selected_list) < max_items:
            changed = False
            for paper_id in ordered_paper_id_list:
                paper_item_list = grouped_map[paper_id]
                if not paper_item_list:
                    continue
                if selected_per_paper_map[paper_id] >= self.per_paper_limit:
                    continue
                selected_list.append(paper_item_list.pop(0))
                selected_per_paper_map[paper_id] += 1
                changed = True
                if len(selected_list) >= max_items:
                    break
            if not changed:
                break
        return selected_list

    def _section_prior(self, section_title: str) -> float:
        lowered = section_title.lower()
        for section_prefix, score in SECTION_PRIOR_MAP.items():
            if lowered.startswith(section_prefix):
                return score
        return 0.02

    def _lexical_overlap(self, query_token_set: set[str], text: str) -> float:
        if not query_token_set:
            return 0.0
        doc_token_set = set(tokenize(text))
        return len(query_token_set & doc_token_set) / max(1, len(query_token_set))

    def _normalize_retrieval_score(self, ranked_item: dict) -> float:
        distance = ranked_item.get("distance")
        if distance is None:
            return float(ranked_item.get("score", 0.0))
        return float(1.0 / (1.0 + float(distance)))

    def _infer_role(self, section_title: str, quote: str) -> EvidenceRole:
        text = f"{section_title} {quote}".lower()
        if "limitation" in text or "weakness" in text:
            return EvidenceRole.LIMITATION
        if "result" in text or "improv" in text or "outperform" in text:
            return EvidenceRole.RESULT
        if "method" in text or "approach" in text or "framework" in text:
            return EvidenceRole.METHOD
        if "however" in text or "contrast" in text or "whereas" in text:
            return EvidenceRole.CONTRAST
        return EvidenceRole.SUPPORT

    def _safe_int(self, value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
