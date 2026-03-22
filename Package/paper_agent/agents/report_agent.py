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

This module implements the review/report agent for Paper Agent.

The agent supports:

- evidence-grounded heuristic review generation
- AutoGen + Ollama multi-agent review generation
"""


import asyncio
import requests

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.ollama import OllamaChatCompletionClient

from paper_agent.models.entities import AnalysisResult, Cluster, Evidence, EvidenceCitation, Paper
from paper_agent.models.enums import TargetType, TaskType
from paper_agent.utils.text_cleaner import extract_keywords, split_sentences


class ReportAgent:
    """
    ReportAgent
    -----------
    Survey and review generation agent.
    """

    def __init__(self, llm_provider: str, llm_model: str, ollama_base_url: str) -> None:
        """
        Function Function:

            Initialize report agent.
        """

        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.ollama_base_url = ollama_base_url
        self._ollama_available: bool | None = None

    def generate(
        self,
        project_id: str,
        question: str,
        paper_list: list[Paper],
        cluster_list: list[Cluster],
        evidence_list: list[Evidence] | None = None,
    ) -> AnalysisResult:
        """
        Function Function:

            Generate evidence-grounded research review markdown.
        """

        citation_list = self._build_citations(evidence_list or [], paper_list)
        if self.llm_provider == "ollama" and self._is_ollama_available():
            markdown_text = self._generate_with_autogen(question, paper_list, cluster_list, citation_list)
        else:
            markdown_text = self._generate_with_heuristic(question, paper_list, cluster_list, citation_list)

        return AnalysisResult(
            project_id=project_id,
            task_type=TaskType.REVIEW,
            target_type=TargetType.COLLECTION,
            target_id=project_id,
            content_md=markdown_text,
            content_json={
                "question": question,
                "paper_count": len(paper_list),
                "cluster_count": len(cluster_list),
                "evidence_count": len(citation_list),
            },
            citations=citation_list[:10],
        )

    def _generate_with_heuristic(
        self,
        question: str,
        paper_list: list[Paper],
        cluster_list: list[Cluster],
        citation_list: list[EvidenceCitation],
    ) -> str:
        """
        Function Function:

            Generate heuristic review markdown.
        """

        keyword_list = extract_keywords([item.title + " " + item.abstract for item in paper_list], limit=8)
        line_list = [
            "# Research Review",
            "",
            "## Research Question",
            question,
            "",
            "## Corpus Overview",
            f"- Paper count: {len(paper_list)}",
            f"- Keywords: {', '.join(keyword_list) if keyword_list else 'n/a'}",
            f"- Evidence count: {len(citation_list)}",
            "",
            "## Topic Clusters",
        ]
        if cluster_list:
            for item in cluster_list:
                line_list.extend(
                    [
                        f"### {item.label}",
                        f"- Papers: {len(item.paper_ids)}",
                        f"- Keywords: {', '.join(item.keywords) if item.keywords else 'n/a'}",
                        f"- Summary: {item.summary}",
                    ]
                )
        else:
            line_list.append("- No clusters were available.")

        line_list.extend(["", "## Representative Papers"])
        for item in paper_list[: min(8, len(paper_list))]:
            summary_sentence_list = split_sentences(item.abstract)
            line_list.append(
                f"- **{item.title}**: {(summary_sentence_list[0] if summary_sentence_list else item.abstract) or 'No abstract.'}"
            )

        line_list.extend(["", "## Evidence Highlights"])
        if citation_list:
            for item in citation_list[:8]:
                line_list.append(f"- **{item.paper_title}** ({item.score:.3f}): {item.quote}")
        else:
            line_list.append("- No supporting evidence chunks were retrieved.")

        line_list.extend(
            [
                "",
                "## Research Gaps",
                "- Further work should compare methods under a unified benchmark with shared evaluation settings.",
                "- Evidence coverage should be expanded with citation graph reasoning and stronger reranking.",
                "- More data sources beyond ArXiv should be integrated for broader recall.",
            ]
        )
        return "\n".join(line_list)

    def _generate_with_autogen(
        self,
        question: str,
        paper_list: list[Paper],
        cluster_list: list[Cluster],
        citation_list: list[EvidenceCitation],
    ) -> str:
        """
        Function Function:

            Generate review via AutoGen + Ollama with fallback.
        """

        try:
            return asyncio.run(self._run_autogen(question, paper_list, cluster_list, citation_list))
        except Exception:
            return self._generate_with_heuristic(question, paper_list, cluster_list, citation_list)

    async def _run_autogen(
        self,
        question: str,
        paper_list: list[Paper],
        cluster_list: list[Cluster],
        citation_list: list[EvidenceCitation],
    ) -> str:
        """
        Function Function:

            Execute AutoGen multi-agent review flow.
        """

        client = OllamaChatCompletionClient(model=self.llm_model, host=self.ollama_base_url)
        analyst_agent = AssistantAgent(
            name="literature_analyst",
            model_client=client,
            system_message=(
                "You analyze scientific literature collections and summarize the main topic routes, "
                "clusters, and research gaps only from supplied evidence."
            ),
        )
        writer_agent = AssistantAgent(
            name="survey_writer",
            model_client=client,
            system_message=(
                "You write concise markdown survey reports with sections "
                "'Research Review', 'Corpus Overview', 'Topic Clusters', 'Evidence Highlights', and 'Research Gaps'. "
                "End with TERMINATE."
            ),
        )
        team = RoundRobinGroupChat(
            participants=[analyst_agent, writer_agent],
            termination_condition=TextMentionTermination("TERMINATE") | MaxMessageTermination(4),
            max_turns=4,
        )
        paper_text = "\n".join(f"- {item.title}: {item.abstract}" for item in paper_list[:10])
        cluster_text = "\n".join(f"- {item.label}: {item.summary}" for item in cluster_list[:10])
        evidence_text = "\n".join(
            f"- {item.paper_title} ({item.score:.3f}): {item.quote}"
            for item in citation_list[:10]
        )
        task = (
            f"Research question:\n{question}\n\n"
            f"Papers:\n{paper_text}\n\n"
            f"Clusters:\n{cluster_text}\n\n"
            f"Evidence:\n{evidence_text}\n\n"
            "Return markdown only."
        )
        task_result = await team.run(task=task)
        final_message = task_result.messages[-1].content if task_result.messages else ""
        return (
            str(final_message).replace("TERMINATE", "").strip()
            or self._generate_with_heuristic(question, paper_list, cluster_list, citation_list)
        )

    def _build_citations(
        self,
        evidence_list: list[Evidence],
        paper_list: list[Paper],
    ) -> list[EvidenceCitation]:
        """
        Function Function:

            Convert ranked evidence into review citations.
        """

        citation_list: list[EvidenceCitation] = []
        seen_chunk_id_set: set[str] = set()
        for item in evidence_list:
            chunk_id = item.chunk_id
            if not chunk_id or chunk_id in seen_chunk_id_set:
                continue
            seen_chunk_id_set.add(chunk_id)
            page_hint = None
            if item.page_start is not None and item.page_end is not None:
                page_hint = f"p.{item.page_start}-{item.page_end}"
            elif item.page_start is not None:
                page_hint = f"p.{item.page_start}"
            citation_list.append(
                EvidenceCitation(
                    paper_id=item.paper_id,
                    chunk_id=chunk_id,
                    paper_title=item.paper_title,
                    quote=item.quote[:280],
                    page_hint=page_hint,
                    score=round(float(item.final_score), 4),
                )
            )

        if citation_list:
            return citation_list

        for item in paper_list[:6]:
            sentence_list = split_sentences(item.abstract)
            if not sentence_list:
                continue
            citation_list.append(
                EvidenceCitation(
                    paper_id=item.paper_id,
                    chunk_id=f"abstract::{item.paper_id}",
                    paper_title=item.title,
                    quote=sentence_list[0],
                    score=0.1,
                )
            )
        return citation_list

    def _is_ollama_available(self) -> bool:
        """
        Function Function:

            Probe local Ollama service once and cache result.
        """

        if self._ollama_available is not None:
            return self._ollama_available
        try:
            response = requests.get(f"{self.ollama_base_url.rstrip('/')}/api/tags", timeout=1.5)
            self._ollama_available = response.status_code == 200
        except Exception:
            self._ollama_available = False
        return self._ollama_available


###################################################################################################
###################################################################################################
### End of file
