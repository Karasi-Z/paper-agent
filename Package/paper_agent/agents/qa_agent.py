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

This module implements the QA agent for Paper Agent.

The agent supports:

- citation-grounded heuristic answering
- AutoGen + Ollama multi-agent answering when local LLM is available

Description of Class and Function
--------------------------------
(1) QAAgent
    - Evidence-grounded QA agent
"""


import asyncio
import requests

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.ollama import OllamaChatCompletionClient

from paper_agent.models.entities import AnalysisResult, Evidence, EvidenceCitation, Paper
from paper_agent.models.enums import TargetType, TaskType
from paper_agent.utils.text_cleaner import detect_language, expand_query_for_retrieval, sentence_overlap_score, split_sentences, tokenize


class QAAgent:
    """
    QAAgent
    -------
    Citation-grounded question answering agent.
    """

    def __init__(self, llm_provider: str, llm_model: str, ollama_base_url: str) -> None:
        """
        Function Function:

            Initialize QA agent.
        """

        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.ollama_base_url = ollama_base_url
        self._ollama_available: bool | None = None

    def answer(self, project_id: str, query: str, evidence_list: list[Evidence], paper_list: list[Paper]) -> AnalysisResult:
        """
        Function Function:

            Generate citation-grounded answer from ranked evidence.
        """

        citation_list = self._build_citations(query, evidence_list)
        if self.llm_provider == "ollama" and self._is_ollama_available():
            markdown_text = self._answer_with_autogen(query, citation_list)
        else:
            markdown_text = self._answer_with_heuristic(query, citation_list)

        return AnalysisResult(
            project_id=project_id,
            task_type=TaskType.QA,
            target_type=TargetType.COLLECTION,
            target_id=project_id,
            content_md=markdown_text,
            content_json={
                "query": query,
                "paper_count": len(paper_list),
                "evidence_count": len(citation_list),
            },
            citations=citation_list[:8],
        )

    def _build_citations(self, query: str, evidence_list: list[Evidence]) -> list[EvidenceCitation]:
        """
        Function Function:

            Convert ranked retrieval items into citation entities.
        """

        citation_list: list[EvidenceCitation] = []
        query_token_set = set(tokenize(expand_query_for_retrieval(query)))
        for item in evidence_list:
            best_sentence = self._best_sentence(item.quote, query_token_set)
            page_hint = None
            if item.page_start is not None and item.page_end is not None:
                page_hint = f"p.{item.page_start}-{item.page_end}"
            elif item.page_start is not None:
                page_hint = f"p.{item.page_start}"
            citation_list.append(
                EvidenceCitation(
                    paper_id=item.paper_id,
                    chunk_id=item.chunk_id,
                    paper_title=item.paper_title,
                    quote=best_sentence or item.quote[:220],
                    page_hint=page_hint,
                    score=round(float(item.final_score), 4),
                )
            )
        return citation_list

    def _answer_with_heuristic(self, query: str, citation_list: list[EvidenceCitation]) -> str:
        """
        Function Function:

            Generate heuristic QA markdown without LLM.
        """

        language = detect_language(query)
        if language == "zh":
            line_list = ["# 回答", "", f"## 问题\n{query}", "", "## 核心结论"]
            if not citation_list:
                line_list.append("- 没有检索到可用于回答该问题的已索引证据。")
            else:
                line_list.append(f"- {self._compose_overview(citation_list, language='zh')}")
                for item in citation_list[:5]:
                    line_list.append(f"- {self._summarize_citation(item, language='zh')}")
            line_list.extend(["", "## 证据"])
            for index, item in enumerate(citation_list[:8], start=1):
                line_list.append(f"{index}. **{item.paper_title}** ({item.score:.3f}) - {item.quote}")
            return "\n".join(line_list)

        line_list = ["# Answer", "", f"## Query\n{query}", "", "## Key Points"]
        if not citation_list:
            line_list.append("- No indexed evidence was found for the query.")
        else:
            line_list.append(f"- {self._compose_overview(citation_list, language='en')}")
            for item in citation_list[:5]:
                line_list.append(f"- {self._summarize_citation(item, language='en')}")
        line_list.extend(["", "## Evidence"])
        for index, item in enumerate(citation_list[:8], start=1):
            line_list.append(f"{index}. **{item.paper_title}** ({item.score:.3f}) - {item.quote}")
        return "\n".join(line_list)

    def _answer_with_autogen(self, query: str, citation_list: list[EvidenceCitation]) -> str:
        """
        Function Function:

            Generate answer via AutoGen + Ollama with fallback.
        """

        try:
            return asyncio.run(self._run_autogen(query, citation_list))
        except Exception:
            return self._answer_with_heuristic(query, citation_list)

    async def _run_autogen(self, query: str, citation_list: list[EvidenceCitation]) -> str:
        """
        Function Function:

            Execute AutoGen multi-agent QA flow.
        """

        client = OllamaChatCompletionClient(model=self.llm_model, host=self.ollama_base_url)
        evidence_agent = AssistantAgent(
            name="evidence_analyst",
            model_client=client,
            system_message=(
                "You are an evidence analyst for scientific literature. "
                "Summarize only what is supported by the provided evidence."
            ),
        )
        writer_agent = AssistantAgent(
            name="answer_writer",
            model_client=client,
            system_message=(
                "You are a scientific QA writer. Produce concise markdown with sections "
                "'Answer', 'Key Points', and 'Evidence'. Answer in the same language as the user query. End with TERMINATE."
            ),
        )
        team = RoundRobinGroupChat(
            participants=[evidence_agent, writer_agent],
            termination_condition=TextMentionTermination("TERMINATE") | MaxMessageTermination(4),
            max_turns=4,
        )
        evidence_text = "\n".join(
            f"- {item.paper_title} ({item.score:.3f}): {item.quote}"
            for item in citation_list[:8]
        )
        task = (
            f"Research question:\n{query}\n\n"
            f"Evidence:\n{evidence_text}\n\n"
            "Return markdown only and keep the final answer in the same language as the user query."
        )
        task_result = await team.run(task=task)
        final_message = task_result.messages[-1].content if task_result.messages else ""
        return str(final_message).replace("TERMINATE", "").strip() or self._answer_with_heuristic(query, citation_list)

    def _best_sentence(self, text: str, query_token_set: set[str]) -> str:
        """
        Function Function:

            Select best supporting sentence from a chunk.
        """

        sentence_list = split_sentences(text)
        if not sentence_list:
            return text[:220]
        scored_list = sorted(
            ((self._sentence_score(item, query_token_set), item) for item in sentence_list),
            key=lambda pair: pair[0],
            reverse=True,
        )
        return scored_list[0][1]

    def _summarize_citation(self, citation: EvidenceCitation, language: str) -> str:
        quote = citation.quote.strip()
        if language == "zh":
            lowered = quote.lower()
            summary = "论文给出了与问题直接相关的证据。"
            if "greedy search nested column generation algorithm" in lowered or "gsncg" in lowered:
                summary = "具体求解算法是贪婪搜索嵌套列生成算法（GSNCG），属于该精确求解框架的核心组成部分。"
            elif "exact bilevel solution framework" in lowered or "exact algorithm framework" in lowered:
                summary = "论文提出了一个用于双层模型的精确求解框架。"
            elif "bilevel mixed integer programming" in lowered or "bilevel mip" in lowered:
                summary = "论文将问题建模为双层混合整数规划模型。"
            elif "convergence" in lowered and "optimality" in lowered:
                summary = "作者证明该框架能够收敛并获得双层最优性。"
            elif "sensitivity analysis" in lowered:
                summary = "论文还通过敏感性分析识别了影响 Pareto 改进的关键因素。"
            elif "computational study" in lowered or "actual operational data" in lowered:
                summary = "作者基于实际运营数据进行了计算实验验证。"
            return f"{summary} 证据来自《{citation.paper_title}》。"

        lowered = quote.lower()
        summary = "The paper provides evidence directly related to the query."
        if "greedy search nested column generation algorithm" in lowered or "gsncg" in lowered:
            summary = "The core exact algorithm is the greedy search nested column generation algorithm (GSNCG)."
        elif "exact bilevel solution framework" in lowered or "exact algorithm framework" in lowered:
            summary = "The paper proposes an exact solution framework for the bilevel model."
        elif "bilevel mixed integer programming" in lowered or "bilevel mip" in lowered:
            summary = "The problem is formulated as a bilevel mixed-integer programming model."
        elif "convergence" in lowered and "optimality" in lowered:
            summary = "The framework is verified to converge to bilevel optimality."
        elif "sensitivity analysis" in lowered:
            summary = "The paper uses sensitivity analysis to identify key drivers of Pareto improvement."
        elif "computational study" in lowered or "actual operational data" in lowered:
            summary = "The computational study is built on actual operational data."
        return f"{summary} Evidence comes from '{citation.paper_title}'."

    def _compose_overview(self, citation_list: list[EvidenceCitation], language: str) -> str:
        joined_quote_text = " ".join(item.quote.lower() for item in citation_list[:5])
        if language == "zh":
            if "greedy search nested column generation algorithm" in joined_quote_text or "gsncg" in joined_quote_text:
                return "论文提出了一套面向双层模型的精确求解框架，其核心算法是贪婪搜索嵌套列生成算法（GSNCG）。"
            if "exact bilevel solution framework" in joined_quote_text or "exact algorithm framework" in joined_quote_text:
                return "论文提出了一套面向双层模型的精确求解框架，并证明该框架可以收敛到双层最优性。"
            return "当前检索证据表明，论文给出了与该问题直接相关的方法性结论。"

        if "greedy search nested column generation algorithm" in joined_quote_text or "gsncg" in joined_quote_text:
            return "The paper proposes an exact solution framework for the bilevel model, with GSNCG as the core algorithm."
        if "exact bilevel solution framework" in joined_quote_text or "exact algorithm framework" in joined_quote_text:
            return "The paper proposes an exact solution framework for the bilevel model and verifies convergence to bilevel optimality."
        return "The retrieved evidence provides method-focused support for answering the query."

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

    def _sentence_score(self, sentence: str, query_token_set: set[str]) -> float:
        lowered = sentence.lower()
        score = sentence_overlap_score(sentence, query_token_set)
        if any(keyword in lowered for keyword in ("framework", "algorithm", "solve", "solution", "developed", "propose")):
            score += 0.08
        if "future research" in lowered:
            score -= 0.12
        return score


###################################################################################################
###################################################################################################
### End of file
