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

This module implements the high-level application service for Paper Agent.

Description of Class and Function
--------------------------------
(1) PaperAgentService
    - Main application service facade
"""


import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from paper_agent.agents.cluster_agent import ClusterAgent
from paper_agent.agents.index_agent import IndexAgent
from paper_agent.agents.library_sync_agent import LibrarySyncAgent
from paper_agent.agents.parse_agent import ParseAgent
from paper_agent.agents.qa_agent import QAAgent
from paper_agent.agents.report_agent import ReportAgent
from paper_agent.agents.search_agent import SearchAgent
from paper_agent.config import AppConfig
from paper_agent.dao.analysis_dao import AnalysisDao
from paper_agent.dao.chunk_dao import ChunkDao
from paper_agent.dao.cluster_dao import ClusterDao
from paper_agent.dao.paper_dao import PaperDao
from paper_agent.dao.project_dao import ProjectDao
from paper_agent.dao.run_dao import RunDao
from paper_agent.dao.run_event_dao import RunEventDao
from paper_agent.models.entities import OperationResult, Paper, ProjectSnapshot, ResearchProject, RunEvent, WorkflowRun
from paper_agent.models.enums import ProjectMode, RunStage, RunStatus
from paper_agent.parsing.service import ParserService
from paper_agent.rag.chunking import ChunkingService
from paper_agent.rag.embedding import build_embedding_provider
from paper_agent.rag.evidence_pack import EvidencePackBuilder
from paper_agent.rag.reranker import PassThroughReranker
from paper_agent.rag.vector_store import RagVectorService
from paper_agent.retrieval.arxiv_client import ArxivClient
from paper_agent.store.chroma_store import ChromaVectorStore
from paper_agent.store.sqlite_store import SQLiteStore
from paper_agent.workflow.graph import ResearchWorkflowGraph
from paper_agent.workflow.runtime_store import RunWorkspaceStore
from paper_agent.workflow.scheduler import WorkflowScheduler


class PaperAgentService:
    """
    PaperAgentService
    -----------------
    Main application service facade.
    """

    def __init__(self, config: AppConfig | None = None) -> None:
        """
        Function Function:

            Initialize service dependencies and workflow runtime.
        """

        self.config = config or AppConfig.from_env()
        self.sqlite_store = SQLiteStore(self.config.db_path)
        self.chroma_store = ChromaVectorStore(self.config.chroma_dir)

        self.project_dao = ProjectDao(self.sqlite_store)
        self.paper_dao = PaperDao(self.sqlite_store)
        self.chunk_dao = ChunkDao(self.sqlite_store)
        self.analysis_dao = AnalysisDao(self.sqlite_store)
        self.cluster_dao = ClusterDao(self.sqlite_store)
        self.run_dao = RunDao(self.sqlite_store)
        self.run_event_dao = RunEventDao(self.sqlite_store)

        self.parser_service = ParserService(
            backend=self.config.parser_backend,
            grobid_url=self.config.grobid_url,
        )
        self.chunking_service = ChunkingService()
        self.embedding_provider = build_embedding_provider(
            provider_name=self.config.embedding_provider,
            model_name=self.config.embedding_model,
            host=self.config.ollama_base_url,
            dim=self.config.vector_dim,
        )
        self.vector_service = RagVectorService(
            embedding_provider=self.embedding_provider,
            chroma_store=self.chroma_store,
            chunk_dao=self.chunk_dao,
        )
        self.reranker = PassThroughReranker()
        self.evidence_builder = EvidencePackBuilder(per_paper_limit=2, max_items=max(self.config.default_top_k, 10))
        self.runtime_store = RunWorkspaceStore(self.config.data_dir)

        self.search_agent = SearchAgent(ArxivClient())
        self.parse_agent = ParseAgent(self.parser_service)
        self.index_agent = IndexAgent(self.chunk_dao, self.vector_service)
        self.library_sync_agent = LibrarySyncAgent(str(self.config.notes_dir), self.parser_service)
        self.cluster_agent = ClusterAgent(max_clusters=self.config.max_clusters)
        self.qa_agent = QAAgent(
            llm_provider=self.config.llm_provider,
            llm_model=self.config.llm_model,
            ollama_base_url=self.config.ollama_base_url,
        )
        self.report_agent = ReportAgent(
            llm_provider=self.config.llm_provider,
            llm_model=self.config.llm_model,
            ollama_base_url=self.config.ollama_base_url,
        )

        self.workflow_graph = ResearchWorkflowGraph(
            project_dao=self.project_dao,
            paper_dao=self.paper_dao,
            chunk_dao=self.chunk_dao,
            analysis_dao=self.analysis_dao,
            cluster_dao=self.cluster_dao,
            run_dao=self.run_dao,
            run_event_dao=self.run_event_dao,
            search_agent=self.search_agent,
            parse_agent=self.parse_agent,
            index_agent=self.index_agent,
            qa_agent=self.qa_agent,
            cluster_agent=self.cluster_agent,
            report_agent=self.report_agent,
            library_sync_agent=self.library_sync_agent,
            chunking_service=self.chunking_service,
            vector_service=self.vector_service,
            reranker=self.reranker,
            evidence_builder=self.evidence_builder,
            runtime_store=self.runtime_store,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        self.workflow_scheduler = WorkflowScheduler(self.workflow_graph)

    def create_project(
        self,
        name: str,
        question: str,
        mode: ProjectMode = ProjectMode.WORKFLOW,
        settings: dict | None = None,
    ) -> ResearchProject:
        """
        Function Function:

            Create new research project.
        """

        project = ResearchProject(name=name, question=question, mode=mode, settings=settings or {})
        return self.project_dao.upsert_project(project)

    def list_projects(self) -> list[ResearchProject]:
        """
        Function Function:

            List all research projects.
        """

        return self.project_dao.list_projects()

    def list_project_papers(self, project_id: str) -> list[Paper]:
        """
        Function Function:

            List all papers attached to one project.
        """

        return self.paper_dao.list_project_papers(project_id)

    def get_project_snapshot(self, project_id: str) -> ProjectSnapshot:
        """
        Function Function:

            Get project snapshot for API and export.
        """

        project = self.project_dao.get_project(project_id)
        if project is None:
            raise KeyError(f"Unknown project_id={project_id}")
        return ProjectSnapshot(
            project=project,
            papers=self.paper_dao.list_project_papers(project_id),
            clusters=self.cluster_dao.list_clusters(project_id),
            analyses=self.analysis_dao.list_analyses(project_id),
        )

    def get_run(self, run_id: str) -> WorkflowRun | None:
        """
        Function Function:

            Fetch workflow run by identifier.
        """

        return self.run_dao.get_run(run_id)

    def get_run_events(self, run_id: str) -> list[RunEvent]:
        """
        Function Function:

            Fetch workflow event stream by run identifier.
        """

        return self.run_event_dao.list_events(run_id)

    def cancel_run(self, run_id: str, reason: str = "Cancelled by user") -> WorkflowRun:
        """
        Function Function:

            Cancel one running workflow by marking it as failed.
        """

        workflow_run = self.run_dao.get_run(run_id)
        if workflow_run is None:
            raise KeyError(f"Unknown run_id={run_id}")
        if workflow_run.status != RunStatus.RUNNING:
            return workflow_run

        workflow_run.status = RunStatus.FAILED
        workflow_run.stage = RunStage.FAILED
        workflow_run.error = reason
        workflow_run.updated_at = datetime.now(timezone.utc)
        workflow_run.state_payload = {
            **workflow_run.state_payload,
            "cancelled": True,
            "cancel_reason": reason,
        }
        self.run_dao.upsert_run(workflow_run)
        self.run_event_dao.insert_event(
            RunEvent(
                run_id=workflow_run.run_id,
                project_id=workflow_run.project_id,
                event_name="run.failed",
                stage=RunStage.FAILED,
                progress=None,
                message=reason,
                payload={"cancelled": True},
            )
        )
        self.runtime_store.write_state(
            project_id=workflow_run.project_id,
            run_id=workflow_run.run_id,
            state_payload=workflow_run.state_payload,
            stage=workflow_run.stage.value,
            status=workflow_run.status.value,
            lifecycle="FAILED",
            error=workflow_run.error,
        )
        self.runtime_store.write_error_report(
            project_id=workflow_run.project_id,
            run_id=workflow_run.run_id,
            failed_stage=RunStage.FAILED.value,
            error=reason,
            last_event_message=reason,
        )
        return workflow_run

    def resume_run(self, run_id: str) -> OperationResult:
        """
        Function Function:

            Resume one workflow from persisted run state.
        """

        workflow_run = self.run_dao.get_run(run_id)
        if workflow_run is None:
            raise KeyError(f"Unknown run_id={run_id}")
        action = workflow_run.state_payload.get("action")
        if not action:
            raise ValueError(f"run_id={run_id} does not contain resumable action state")
        resume_from_stage = workflow_run.state_payload.get("last_checkpoint_stage")
        if not resume_from_stage:
            raise ValueError(f"run_id={run_id} does not contain checkpoint state for resume")
        replay_kwargs = {
            key: value
            for key, value in workflow_run.state_payload.items()
            if key
            not in {
                "project_id",
                "run_id",
                "payload_type",
                "payload_count",
                "result_id",
                "paper_id_list",
                "cluster_id_list",
                "failed_stage",
                "last_checkpoint_stage",
                "last_checkpoint_at",
            }
        }
        replay_kwargs["resumed_from_run_id"] = run_id
        replay_kwargs["resume_from_stage"] = resume_from_stage
        replay_kwargs.pop("action", None)
        return self._run_workflow(workflow_run.project_id, action, **replay_kwargs)

    def search_catalog(
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

            Search public paper catalog without attaching to project.
        """

        return self.search_agent.search(
            query=query,
            limit=limit,
            author=author,
            categories=categories or [],
            from_year=from_year,
            to_year=to_year,
        )

    def import_text_paper(
        self,
        project_id: str,
        title: str,
        content: str,
        authors: list[str] | None = None,
        abstract: str = "",
        tags: list[str] | None = None,
        source: str = "local",
    ) -> Paper:
        """
        Function Function:

            Import paper from raw text.
        """

        paper = Paper(
            title=title,
            authors=authors or [],
            abstract=abstract,
            tags=tags or [],
            source=source,
            content_text=content,
        )
        self.paper_dao.upsert_paper(paper)
        self.paper_dao.attach_paper_to_project(project_id, paper.paper_id)
        return paper

    def import_file_paper(
        self,
        project_id: str,
        path: str,
        title: str | None = None,
        source: str = "local",
    ) -> Paper:
        """
        Function Function:

            Import paper from local file.
        """

        file_path = Path(path)
        parse_result = self.parser_service.parse_file(file_path, fallback_title=title or file_path.stem)
        paper = Paper(
            title=parse_result.title,
            abstract=parse_result.abstract,
            source=source,
            pdf_path=str(file_path),
            content_text=parse_result.full_text,
        )
        self.paper_dao.upsert_paper(paper)
        self.paper_dao.attach_paper_to_project(project_id, paper.paper_id)
        return paper

    def search_and_add(
        self,
        project_id: str,
        query: str,
        limit: int = 10,
        author: str | None = None,
        categories: list[str] | None = None,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> OperationResult:
        """
        Function Function:

            Search papers and attach them to project via LangGraph.
        """

        return self._run_workflow(
            project_id,
            "search_add",
            query=query,
            limit=limit,
            author=author,
            categories=categories or [],
            from_year=from_year,
            to_year=to_year,
        )

    def sync_library(
        self,
        project_id: str,
        provider: str,
        library_path: str,
        collection_id: str | None = None,
        library_options: dict | None = None,
    ) -> OperationResult:
        """
        Function Function:

            Sync literature manager export via LangGraph.
        """

        return self._run_workflow(
            project_id,
            "sync_library",
            provider=provider,
            library_path=library_path,
            collection_id=collection_id,
            library_options=library_options or {},
        )

    def build_index(self, project_id: str) -> OperationResult:
        """
        Function Function:

            Build retrieval index for project papers.
        """

        return self._run_workflow(project_id, "build_index")

    def ask(self, project_id: str, query: str, top_k: int | None = None) -> OperationResult:
        """
        Function Function:

            Execute project-level question answering.
        """

        return self._run_workflow(project_id, "ask", query=query, top_k=top_k or self.config.default_top_k)

    def cluster_project(self, project_id: str) -> OperationResult:
        """
        Function Function:

            Execute project-level clustering.
        """

        return self._run_workflow(project_id, "cluster")

    def generate_review(self, project_id: str) -> OperationResult:
        """
        Function Function:

            Generate project review report.
        """

        return self._run_workflow(project_id, "review", top_k=max(self.config.default_top_k, 10))

    def run_research_workflow(
        self,
        project_id: str,
        query: str,
        limit: int = 10,
        review: bool = True,
        cluster: bool = True,
        author: str | None = None,
        categories: list[str] | None = None,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> OperationResult:
        """
        Function Function:

            Run configurable search-index-analysis workflow.
        """

        return self._run_workflow(
            project_id,
            "research_workflow",
            query=query,
            limit=limit,
            review=review,
            cluster=cluster,
            author=author,
            categories=categories or [],
            from_year=from_year,
            to_year=to_year,
            top_k=max(self.config.default_top_k, 10),
        )

    def push_note_to_library(
        self,
        project_id: str,
        provider: str,
        library_path: str = "",
        paper_id: str | None = None,
        item_id: str | None = None,
        note_md: str | None = None,
        result_id: str | None = None,
        prefer_task_type: str | None = "review",
        library_options: dict | None = None,
    ) -> dict[str, str | None]:
        """
        Function Function:

            Push one analysis note to literature manager backend.
        """

        resolved_item_id, resolved_paper_id = self._resolve_library_item_target(
            project_id=project_id,
            provider=provider,
            paper_id=paper_id,
            item_id=item_id,
        )
        resolved_note_md, resolved_result_id = self._resolve_note_content(
            project_id=project_id,
            note_md=note_md,
            result_id=result_id,
            prefer_task_type=prefer_task_type,
        )
        push_result = self.library_sync_agent.push_note(
            provider=provider,
            library_path=library_path,
            item_id=resolved_item_id,
            note_md=resolved_note_md,
            library_options=library_options or {},
        )
        return {
            "project_id": project_id,
            "provider": provider,
            "paper_id": resolved_paper_id,
            "item_id": resolved_item_id,
            "result_id": resolved_result_id,
            "note_ref": push_result.get("note_ref"),
            "backup_path": push_result.get("backup_path"),
        }

    def export_project_markdown(self, project_id: str) -> str:
        """
        Function Function:

            Export project snapshot as Markdown.
        """

        snapshot = self.get_project_snapshot(project_id)
        line_list = [
            f"# {snapshot.project.name}",
            "",
            "## Research Question",
            snapshot.project.question,
            "",
            "## Papers",
        ]
        for item in snapshot.papers:
            line_list.append(f"- {item.title} | source={item.source} | paper_id={item.paper_id}")
        if snapshot.clusters:
            line_list.extend(["", "## Clusters"])
            for item in snapshot.clusters:
                line_list.append(f"### {item.label}")
                line_list.append(f"- Papers: {len(item.paper_ids)}")
                line_list.append(f"- Keywords: {', '.join(item.keywords) if item.keywords else 'n/a'}")
                if item.summary:
                    line_list.append(f"- Summary: {item.summary}")
        line_list.extend(["", "## Analyses"])
        for item in snapshot.analyses:
            line_list.append(item.content_md)
            line_list.append("")
        markdown_text = "\n".join(line_list).strip() + "\n"
        with self.runtime_store.resource_lock(project_id, "resource"):
            self.runtime_store.write_project_export(project_id, "project_export.md", markdown_text)
        return markdown_text

    def export_project_json(self, project_id: str) -> str:
        snapshot = self.get_project_snapshot(project_id)
        json_text = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2)
        with self.runtime_store.resource_lock(project_id, "resource"):
            self.runtime_store.write_project_export(project_id, "project_export.json", json_text)
        return json_text

    def export_project_csv(self, project_id: str) -> str:
        snapshot = self.get_project_snapshot(project_id)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["paper_id", "title", "source", "published_at", "authors", "tags", "abstract"],
        )
        writer.writeheader()
        for item in snapshot.papers:
            writer.writerow(
                {
                    "paper_id": item.paper_id,
                    "title": item.title,
                    "source": item.source,
                    "published_at": item.published_at or "",
                    "authors": "; ".join(item.authors),
                    "tags": "; ".join(item.tags),
                    "abstract": item.abstract,
                }
            )
        csv_text = output.getvalue()
        with self.runtime_store.resource_lock(project_id, "resource"):
            self.runtime_store.write_project_export(project_id, "papers.csv", csv_text)
        return csv_text

    def export_project_bibtex(self, project_id: str) -> str:
        paper_list = self.paper_dao.list_project_papers(project_id)
        block_list: list[str] = []
        for item in paper_list:
            author_text = " and ".join(item.authors) if item.authors else "Unknown"
            year_text = ""
            if item.published_at:
                year_text = str(item.published_at)[:4]
            key = (item.arxiv_id or item.source_key or item.paper_id).replace(" ", "_")
            block_list.append(
                f"@article{{{key},\n"
                f"  title = {{{item.title}}},\n"
                f"  author = {{{author_text}}},\n"
                f"  year = {{{year_text}}},\n"
                f"  abstract = {{{item.abstract}}}\n"
                f"}}"
            )
        bibtex_text = "\n\n".join(block_list)
        with self.runtime_store.resource_lock(project_id, "resource"):
            self.runtime_store.write_project_export(project_id, "references.bib", bibtex_text)
        return bibtex_text

    def export_project(self, project_id: str, fmt: str = "markdown") -> str:
        normalized_format = fmt.lower()
        if normalized_format in {"md", "markdown"}:
            return self.export_project_markdown(project_id)
        if normalized_format == "json":
            return self.export_project_json(project_id)
        if normalized_format == "csv":
            return self.export_project_csv(project_id)
        if normalized_format in {"bib", "bibtex"}:
            return self.export_project_bibtex(project_id)
        raise ValueError(f"Unsupported export format: {fmt}")

    def route_auto_mode(self, project_id: str, query: str) -> tuple[ProjectMode, str]:
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return ProjectMode.WORKSPACE, "empty query defaults to workspace snapshot"

        workspace_marker_list = ["export", "show project", "show papers", "workspace", "snapshot", "list papers"]
        if any(marker in normalized_query for marker in workspace_marker_list):
            return ProjectMode.WORKSPACE, "workspace-oriented request detected"

        workflow_marker_list = ["survey", "review", "workflow", "compare", "cluster", "research plan", "literature review"]
        token_count = len(normalized_query.split())
        if any(marker in normalized_query for marker in workflow_marker_list) or token_count >= 12:
            return ProjectMode.WORKFLOW, "multi-step research intent detected"

        return ProjectMode.CHAT, "focused question routed to chat QA"

    def run_auto(self, project_id: str, query: str, limit: int = 10, top_k: int | None = None) -> dict:
        mode, rationale = self.route_auto_mode(project_id=project_id, query=query)
        if mode == ProjectMode.WORKSPACE:
            return {
                "mode": mode.value,
                "rationale": rationale,
                "run_id": None,
                "content_md": self.export_project_markdown(project_id),
            }
        if mode == ProjectMode.WORKFLOW:
            operation = self.run_research_workflow(project_id=project_id, query=query, limit=limit)
            return {
                "mode": mode.value,
                "rationale": rationale,
                "run_id": operation.run.run_id,
                "content_md": operation.payload.content_md,
            }

        operation = self.ask(project_id=project_id, query=query, top_k=top_k or self.config.default_top_k)
        return {
            "mode": mode.value,
            "rationale": rationale,
            "run_id": operation.run.run_id,
            "content_md": operation.payload.content_md,
        }

    def _resolve_library_item_target(
        self,
        project_id: str,
        provider: str,
        paper_id: str | None,
        item_id: str | None,
    ) -> tuple[str, str | None]:
        """
        Function Function:

            Resolve literature-manager item target from item or paper identifier.
        """

        if item_id:
            return item_id, paper_id

        if paper_id is None:
            raise ValueError("paper_id or item_id is required for note push")

        paper = self.paper_dao.get_paper(paper_id)
        if paper is None:
            raise KeyError(f"Unknown paper_id={paper_id}")

        project_paper_id_set = {item.paper_id for item in self.paper_dao.list_project_papers(project_id)}
        if paper.paper_id not in project_paper_id_set:
            raise ValueError(f"paper_id={paper_id} is not attached to project_id={project_id}")

        resolved_item_id = paper.source_key or paper.paper_id
        if provider == "zotero" and paper.source_key is None:
            raise ValueError("paper.source_key is required to push note back to Zotero")
        return resolved_item_id, paper.paper_id

    def _resolve_note_content(
        self,
        project_id: str,
        note_md: str | None,
        result_id: str | None,
        prefer_task_type: str | None,
    ) -> tuple[str, str | None]:
        """
        Function Function:

            Resolve note body from explicit text or project analyses.
        """

        if note_md:
            return note_md, result_id

        analysis_list = self.analysis_dao.list_analyses(project_id)
        if result_id is not None:
            for item in analysis_list:
                if item.result_id == result_id:
                    return item.content_md, item.result_id
            raise KeyError(f"Unknown result_id={result_id}")

        if prefer_task_type:
            filtered_list = [item for item in analysis_list if item.task_type.value == prefer_task_type]
            if filtered_list:
                return filtered_list[-1].content_md, filtered_list[-1].result_id

        review_list = [item for item in analysis_list if item.task_type.value == "review"]
        if review_list:
            return review_list[-1].content_md, review_list[-1].result_id

        if analysis_list:
            return analysis_list[-1].content_md, analysis_list[-1].result_id

        return self.export_project_markdown(project_id), None

    def create_run(self, project_id: str, action: str, **kwargs) -> WorkflowRun:
        """
        Function Function:

            Create one workflow run record and initialize run workspace.
        """

        initial_payload = {"action": action, **kwargs}
        workflow_run = WorkflowRun(
            project_id=project_id,
            stage=RunStage.DRAFT,
            status=RunStatus.RUNNING,
            state_payload=initial_payload,
        )
        self.run_dao.upsert_run(workflow_run)
        self.runtime_store.ensure_run_workspace(
            project_id=project_id,
            run_id=workflow_run.run_id,
            action=action,
            payload=initial_payload,
        )
        self.runtime_store.write_state(
            project_id=project_id,
            run_id=workflow_run.run_id,
            state_payload=initial_payload,
            stage=workflow_run.stage.value,
            status=workflow_run.status.value,
            lifecycle="RUNNING",
        )
        self.run_event_dao.insert_event(
            RunEvent(
                run_id=workflow_run.run_id,
                project_id=project_id,
                event_name="run.started",
                stage=RunStage.DRAFT,
                progress=0.0,
                message=f"Workflow started for action={action}.",
                payload=initial_payload,
            )
        )
        return workflow_run

    def execute_run(self, run_id: str) -> OperationResult:
        """
        Function Function:

            Execute one existing workflow run by run identifier.
        """

        workflow_run = self.run_dao.get_run(run_id)
        if workflow_run is None:
            raise KeyError(f"Unknown run_id={run_id}")
        action = workflow_run.state_payload.get("action")
        if not action:
            raise ValueError(f"run_id={run_id} does not contain executable action")

        execution_kwargs = {
            key: value
            for key, value in workflow_run.state_payload.items()
            if key
            not in {
                "action",
                "payload_type",
                "payload_count",
                "result_id",
                "paper_id_list",
                "cluster_id_list",
                "failed_stage",
                "last_checkpoint_stage",
                "last_checkpoint_at",
            }
        }
        project_id = workflow_run.project_id
        try:
            project_lock_timeout = 30.0
            with self.runtime_store.project_lock(project_id, timeout_seconds=project_lock_timeout):
                if action in {"build_index", "research_workflow", "review", "search_add", "sync_library"}:
                    with self.runtime_store.resource_lock(project_id, "resource", timeout_seconds=project_lock_timeout):
                        final_state = self.workflow_scheduler.run(
                            {
                                "run_id": workflow_run.run_id,
                                "project_id": project_id,
                                "action": action,
                                **execution_kwargs,
                            }
                        )
                else:
                    final_state = self.workflow_scheduler.run(
                        {
                            "run_id": workflow_run.run_id,
                            "project_id": project_id,
                            "action": action,
                            **execution_kwargs,
                        }
                    )
            latest_run = self.run_dao.get_run(workflow_run.run_id) or workflow_run
            return OperationResult(run=latest_run, payload=final_state.get("payload"))
        except Exception as exc:
            workflow_run = self.run_dao.get_run(workflow_run.run_id) or workflow_run
            failed_stage = workflow_run.stage
            workflow_run.stage = RunStage.FAILED
            workflow_run.status = RunStatus.FAILED
            workflow_run.error = str(exc)
            workflow_run.state_payload = {
                **workflow_run.state_payload,
                "action": action,
                "failed_stage": failed_stage.value if hasattr(failed_stage, "value") else str(failed_stage),
            }
            self.run_dao.upsert_run(workflow_run)
            self.run_event_dao.insert_event(
                RunEvent(
                    run_id=workflow_run.run_id,
                    project_id=project_id,
                    event_name="run.failed",
                    stage=RunStage.FAILED,
                    progress=None,
                    message=str(exc),
                    payload=workflow_run.state_payload,
                )
            )
            self.runtime_store.write_state(
                project_id=project_id,
                run_id=workflow_run.run_id,
                state_payload=workflow_run.state_payload,
                stage=workflow_run.stage.value,
                status=workflow_run.status.value,
                lifecycle="FAILED",
                error=workflow_run.error,
            )
            event_list = self.run_event_dao.list_events(workflow_run.run_id)
            self.runtime_store.write_error_report(
                project_id=project_id,
                run_id=workflow_run.run_id,
                failed_stage=workflow_run.state_payload.get("failed_stage", RunStage.FAILED.value),
                error=str(exc),
                last_event_message=event_list[-1].message if event_list else None,
            )
            raise

    def _run_workflow(self, project_id: str, action: str, **kwargs) -> OperationResult:
        """
        Function Function:

            Run LangGraph workflow and return operation result.
        """

        workflow_run = self.create_run(project_id=project_id, action=action, **kwargs)
        return self.execute_run(workflow_run.run_id)


###################################################################################################
###################################################################################################
### End of file
