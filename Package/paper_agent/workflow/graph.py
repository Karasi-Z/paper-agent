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

This module implements the LangGraph workflow for Paper Agent.

Description of Class and Function
--------------------------------
(1) ResearchWorkflowGraph
    - LangGraph workflow compiler and node definitions
"""


from datetime import datetime, timezone
import json

from langgraph.graph import END, START, StateGraph

from paper_agent.dao.analysis_dao import AnalysisDao
from paper_agent.dao.chunk_dao import ChunkDao
from paper_agent.dao.cluster_dao import ClusterDao
from paper_agent.dao.paper_dao import PaperDao
from paper_agent.dao.project_dao import ProjectDao
from paper_agent.dao.run_dao import RunDao
from paper_agent.dao.run_event_dao import RunEventDao
from paper_agent.models.entities import RunEvent
from paper_agent.models.enums import EntityStatus, RunStage, RunStatus
from paper_agent.rag.chunking import ChunkingService
from paper_agent.rag.evidence_pack import EvidencePackBuilder
from paper_agent.rag.reranker import PassThroughReranker
from paper_agent.rag.vector_store import RagVectorService
from paper_agent.workflow.runtime_store import RunWorkspaceStore
from paper_agent.workflow.state import ResearchWorkflowState


class ResearchWorkflowGraph:
    """
    ResearchWorkflowGraph
    ---------------------
    LangGraph compiler and execution nodes.
    """

    STAGE_PROGRESS_MAP = {
        RunStage.DRAFT: 0.0,
        RunStage.SEARCHING: 0.15,
        RunStage.SYNCING_LIBRARY: 0.2,
        RunStage.PARSING: 0.35,
        RunStage.INDEXING: 0.55,
        RunStage.CLUSTERING: 0.75,
        RunStage.ANALYZING: 0.9,
        RunStage.DONE: 1.0,
        RunStage.FAILED: None,
    }

    def __init__(
        self,
        project_dao: ProjectDao,
        paper_dao: PaperDao,
        chunk_dao: ChunkDao,
        analysis_dao: AnalysisDao,
        cluster_dao: ClusterDao,
        run_dao: RunDao,
        run_event_dao: RunEventDao,
        search_agent,
        parse_agent,
        index_agent,
        qa_agent,
        cluster_agent,
        report_agent,
        library_sync_agent,
        chunking_service: ChunkingService,
        vector_service: RagVectorService,
        reranker: PassThroughReranker,
        evidence_builder: EvidencePackBuilder,
        runtime_store: RunWorkspaceStore,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        """
        Function Function:

            Initialize workflow graph with DAO and agent dependencies.
        """

        self.project_dao = project_dao
        self.paper_dao = paper_dao
        self.chunk_dao = chunk_dao
        self.analysis_dao = analysis_dao
        self.cluster_dao = cluster_dao
        self.run_dao = run_dao
        self.run_event_dao = run_event_dao
        self.search_agent = search_agent
        self.parse_agent = parse_agent
        self.index_agent = index_agent
        self.qa_agent = qa_agent
        self.cluster_agent = cluster_agent
        self.report_agent = report_agent
        self.library_sync_agent = library_sync_agent
        self.chunking_service = chunking_service
        self.vector_service = vector_service
        self.reranker = reranker
        self.evidence_builder = evidence_builder
        self.runtime_store = runtime_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.compiled_graph = self._build_graph()

    def invoke(self, workflow_state: ResearchWorkflowState) -> ResearchWorkflowState:
        """
        Function Function:

            Invoke compiled LangGraph workflow.
        """

        return self.compiled_graph.invoke(workflow_state)

    def _build_graph(self):
        """
        Function Function:

            Build compiled LangGraph state graph.
        """

        graph_builder = StateGraph(ResearchWorkflowState)
        graph_builder.add_node("search_add", self.search_add_node)
        graph_builder.add_node("sync_library", self.sync_library_node)
        graph_builder.add_node("ensure_index", self.ensure_index_node)
        graph_builder.add_node("qa", self.qa_node)
        graph_builder.add_node("cluster", self.cluster_node)
        graph_builder.add_node("review", self.review_node)
        graph_builder.add_node("finish", self.finish_node)

        graph_builder.add_conditional_edges(
            START,
            self.route_start,
            {
                "search_add": "search_add",
                "sync_library": "sync_library",
                "ensure_index": "ensure_index",
                "finish": "finish",
            },
        )
        graph_builder.add_conditional_edges(
            "search_add",
            self.route_after_search,
            {
                "ensure_index": "ensure_index",
                "finish": "finish",
            },
        )
        graph_builder.add_edge("sync_library", "finish")
        graph_builder.add_conditional_edges(
            "ensure_index",
            self.route_after_index,
            {
                "qa": "qa",
                "cluster": "cluster",
                "review": "review",
                "finish": "finish",
            },
        )
        graph_builder.add_conditional_edges(
            "cluster",
            self.route_after_cluster,
            {
                "review": "review",
                "finish": "finish",
            },
        )
        graph_builder.add_edge("qa", "finish")
        graph_builder.add_edge("review", "finish")
        graph_builder.add_edge("finish", END)
        return graph_builder.compile()

    def route_start(self, workflow_state: ResearchWorkflowState) -> str:
        """
        Function Function:

            Route workflow from graph start.
        """

        if workflow_state.get("resume_from_stage"):
            return self._resolve_resume_route(workflow_state)

        action = workflow_state.get("action")
        if action in {"search_add", "research_workflow"}:
            return "search_add"
        if action == "sync_library":
            return "sync_library"
        return "ensure_index"

    def route_after_search(self, workflow_state: ResearchWorkflowState) -> str:
        """
        Function Function:

            Route workflow after search step.
        """

        if workflow_state.get("action") == "research_workflow":
            return "ensure_index"
        return "finish"

    def route_after_index(self, workflow_state: ResearchWorkflowState) -> str:
        """
        Function Function:

            Route workflow after index step.
        """

        action = workflow_state.get("action")
        if action == "ask":
            return "qa"
        if action == "cluster":
            return "cluster"
        if action == "review":
            return "cluster"
        if action == "research_workflow":
            if workflow_state.get("cluster", True):
                return "cluster"
            if workflow_state.get("review", True):
                return "review"
        return "finish"

    def route_after_cluster(self, workflow_state: ResearchWorkflowState) -> str:
        """
        Function Function:

            Route workflow after clustering step.
        """

        action = workflow_state.get("action")
        if action == "review":
            return "review"
        if action == "research_workflow" and workflow_state.get("review", True):
            return "review"
        return "finish"

    def search_add_node(self, workflow_state: ResearchWorkflowState) -> ResearchWorkflowState:
        """
        Function Function:

            Search candidate papers and attach them to project.
        """

        self._assert_not_cancelled(workflow_state["run_id"])
        self._update_run(
            workflow_state["run_id"],
            RunStage.SEARCHING,
            workflow_state,
            message="Searching ArXiv and collecting candidate papers.",
        )
        paper_list = self.search_agent.search(
            query=workflow_state.get("query", ""),
            limit=workflow_state.get("limit", 10),
            author=workflow_state.get("author"),
            categories=workflow_state.get("categories", []),
            from_year=workflow_state.get("from_year"),
            to_year=workflow_state.get("to_year"),
        )
        self._assert_not_cancelled(workflow_state["run_id"])
        for item in paper_list:
            self._assert_not_cancelled(workflow_state["run_id"])
            self.paper_dao.upsert_paper(item)
            self.paper_dao.attach_paper_to_project(workflow_state["project_id"], item.paper_id)
        self._checkpoint_run(
            workflow_state=workflow_state,
            stage=RunStage.SEARCHING,
            checkpoint_payload={"paper_id_list": [item.paper_id for item in paper_list]},
        )
        return {
            **workflow_state,
            "payload": paper_list,
            "paper_id_list": [item.paper_id for item in paper_list],
        }

    def sync_library_node(self, workflow_state: ResearchWorkflowState) -> ResearchWorkflowState:
        """
        Function Function:

            Synchronize papers from literature manager export.
        """

        self._assert_not_cancelled(workflow_state["run_id"])
        self._update_run(
            workflow_state["run_id"],
            RunStage.SYNCING_LIBRARY,
            workflow_state,
            message="Synchronizing literature manager items.",
        )
        paper_list = self.library_sync_agent.sync(
            provider=workflow_state["provider"],
            library_path=workflow_state["library_path"],
            collection_id=workflow_state.get("collection_id"),
            library_options=workflow_state.get("library_options"),
        )
        self._assert_not_cancelled(workflow_state["run_id"])
        for item in paper_list:
            self._assert_not_cancelled(workflow_state["run_id"])
            self.paper_dao.upsert_paper(item)
            self.paper_dao.attach_paper_to_project(workflow_state["project_id"], item.paper_id)
        self._checkpoint_run(
            workflow_state=workflow_state,
            stage=RunStage.SYNCING_LIBRARY,
            checkpoint_payload={"paper_id_list": [item.paper_id for item in paper_list]},
        )
        return {
            **workflow_state,
            "payload": paper_list,
            "paper_id_list": [item.paper_id for item in paper_list],
        }

    def ensure_index_node(self, workflow_state: ResearchWorkflowState) -> ResearchWorkflowState:
        """
        Function Function:

            Parse and index all project papers.
        """

        self._assert_not_cancelled(workflow_state["run_id"])
        self._update_run(
            workflow_state["run_id"],
            RunStage.PARSING,
            workflow_state,
            message="Parsing project papers into structured text.",
        )
        indexed_paper_list = []
        paper_list = self.paper_dao.list_project_papers(workflow_state["project_id"])
        for paper in paper_list:
            self._assert_not_cancelled(workflow_state["run_id"])
            parse_result = self.parse_agent.parse_paper(paper)
            paper.content_text = parse_result.full_text
            if not paper.abstract:
                paper.abstract = parse_result.abstract
            paper.status = EntityStatus.INDEXED
            self.paper_dao.upsert_paper(paper)
            chunk_list = self.chunking_service.chunk_document(
                parse_result=parse_result,
                paper_id=paper.paper_id,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            self.index_agent.index_paper(
                project_id=workflow_state["project_id"],
                paper=paper,
                chunk_list=chunk_list,
            )
            indexed_paper_list.append(paper)

        self._update_run(
            workflow_state["run_id"],
            RunStage.INDEXING,
            {"paper_count": len(indexed_paper_list)},
            message=f"Indexed {len(indexed_paper_list)} papers into retrieval store.",
        )
        self._checkpoint_run(
            workflow_state=workflow_state,
            stage=RunStage.INDEXING,
            checkpoint_payload={
                "paper_count": len(indexed_paper_list),
                "paper_id_list": [item.paper_id for item in indexed_paper_list],
            },
        )
        return {
            **workflow_state,
            "payload": indexed_paper_list if workflow_state.get("action") == "build_index" else workflow_state.get("payload"),
            "paper_id_list": [item.paper_id for item in indexed_paper_list],
        }

    def qa_node(self, workflow_state: ResearchWorkflowState) -> ResearchWorkflowState:
        """
        Function Function:

            Execute RAG evidence retrieval and QA generation.
        """

        self._assert_not_cancelled(workflow_state["run_id"])
        self._update_run(
            workflow_state["run_id"],
            RunStage.ANALYZING,
            workflow_state,
            message="Retrieving evidence and generating answer.",
        )
        paper_list = self.paper_dao.list_project_papers(workflow_state["project_id"])
        ranked_item_list = self.vector_service.search_chunks(
            project_id=workflow_state["project_id"],
            query=workflow_state.get("query", ""),
            top_k=workflow_state.get("top_k", 5),
        )
        ranked_item_list = self.reranker.rerank(
            ranked_item_list=ranked_item_list,
            query=workflow_state.get("query", ""),
        )
        self._assert_not_cancelled(workflow_state["run_id"])
        evidence_list = self.evidence_builder.build(
            query=workflow_state.get("query", ""),
            ranked_item_list=ranked_item_list,
            max_items=max(workflow_state.get("top_k", 5), 8),
        )
        self.runtime_store.write_artifact(
            project_id=workflow_state["project_id"],
            run_id=workflow_state["run_id"],
            relative_path="evidence_pack.json",
            payload=[item.model_dump(mode="json") for item in evidence_list],
        )
        analysis_result = self.qa_agent.answer(
            project_id=workflow_state["project_id"],
            query=workflow_state.get("query", ""),
            evidence_list=evidence_list,
            paper_list=paper_list,
        )
        self.analysis_dao.upsert_analysis(analysis_result)
        self.runtime_store.write_text_artifact(
            project_id=workflow_state["project_id"],
            run_id=workflow_state["run_id"],
            relative_path="final.md",
            content=analysis_result.content_md,
        )
        self._emit_event(
            run_id=workflow_state["run_id"],
            project_id=workflow_state["project_id"],
            event_name="run.partial_result",
            stage=RunStage.ANALYZING,
            progress=0.95,
            message="Question answering result generated.",
            payload={"result_id": analysis_result.result_id, "task_type": analysis_result.task_type.value},
        )
        self._checkpoint_run(
            workflow_state=workflow_state,
            stage=RunStage.ANALYZING,
            checkpoint_payload={
                "result_id": analysis_result.result_id,
                "task_type": analysis_result.task_type.value,
                "evidence_count": len(evidence_list),
            },
        )
        return {**workflow_state, "payload": analysis_result}

    def cluster_node(self, workflow_state: ResearchWorkflowState) -> ResearchWorkflowState:
        """
        Function Function:

            Execute collection clustering.
        """

        self._assert_not_cancelled(workflow_state["run_id"])
        self._update_run(
            workflow_state["run_id"],
            RunStage.CLUSTERING,
            workflow_state,
            message="Clustering indexed papers into topical groups.",
        )
        paper_list = self.paper_dao.list_project_papers(workflow_state["project_id"])
        paper_id_list = [item.paper_id for item in paper_list]
        ordered_id_list, paper_matrix = self.vector_service.get_paper_matrix(paper_id_list)
        cluster_list = self.cluster_agent.cluster(
            project_id=workflow_state["project_id"],
            paper_list=paper_list,
            ordered_paper_ids=ordered_id_list,
            paper_matrix=paper_matrix,
        )
        self._assert_not_cancelled(workflow_state["run_id"])
        self.cluster_dao.replace_clusters(workflow_state["project_id"], cluster_list)
        self._emit_event(
            run_id=workflow_state["run_id"],
            project_id=workflow_state["project_id"],
            event_name="run.partial_result",
            stage=RunStage.CLUSTERING,
            progress=0.82,
            message="Topic clusters generated.",
            payload={"cluster_count": len(cluster_list)},
        )
        self._checkpoint_run(
            workflow_state=workflow_state,
            stage=RunStage.CLUSTERING,
            checkpoint_payload={
                "cluster_count": len(cluster_list),
                "cluster_id_list": [item.cluster_id for item in cluster_list],
            },
        )
        return {
            **workflow_state,
            "payload": cluster_list if workflow_state.get("action") == "cluster" else workflow_state.get("payload"),
            "cluster_id_list": [item.cluster_id for item in cluster_list],
        }

    def review_node(self, workflow_state: ResearchWorkflowState) -> ResearchWorkflowState:
        """
        Function Function:

            Execute review generation.
        """

        self._assert_not_cancelled(workflow_state["run_id"])
        self._update_run(
            workflow_state["run_id"],
            RunStage.ANALYZING,
            workflow_state,
            message="Retrieving evidence and generating review report.",
        )
        project = self.project_dao.get_project(workflow_state["project_id"])
        paper_list = self.paper_dao.list_project_papers(workflow_state["project_id"])
        cluster_list = self.cluster_dao.list_clusters(workflow_state["project_id"])
        review_query = workflow_state.get("query") or (project.question if project else "")
        ranked_item_list = self.vector_service.search_chunks(
            project_id=workflow_state["project_id"],
            query=review_query,
            top_k=max(workflow_state.get("top_k", 5), 10),
        )
        ranked_item_list = self.reranker.rerank(
            ranked_item_list=ranked_item_list,
            query=review_query,
        )
        self._assert_not_cancelled(workflow_state["run_id"])
        evidence_list = self.evidence_builder.build(
            query=review_query,
            ranked_item_list=ranked_item_list,
            max_items=max(workflow_state.get("top_k", 5), 10),
        )
        self.runtime_store.write_artifact(
            project_id=workflow_state["project_id"],
            run_id=workflow_state["run_id"],
            relative_path="evidence_pack.json",
            payload=[item.model_dump(mode="json") for item in evidence_list],
        )
        analysis_result = self.report_agent.generate(
            project_id=workflow_state["project_id"],
            question=project.question if project else "",
            paper_list=paper_list,
            cluster_list=cluster_list,
            evidence_list=evidence_list,
        )
        self.analysis_dao.upsert_analysis(analysis_result)
        self.runtime_store.write_text_artifact(
            project_id=workflow_state["project_id"],
            run_id=workflow_state["run_id"],
            relative_path="final.md",
            content=analysis_result.content_md,
        )
        self._emit_event(
            run_id=workflow_state["run_id"],
            project_id=workflow_state["project_id"],
            event_name="run.partial_result",
            stage=RunStage.ANALYZING,
            progress=0.97,
            message="Review report generated.",
            payload={"result_id": analysis_result.result_id, "task_type": analysis_result.task_type.value},
        )
        self._checkpoint_run(
            workflow_state=workflow_state,
            stage=RunStage.ANALYZING,
            checkpoint_payload={
                "result_id": analysis_result.result_id,
                "task_type": analysis_result.task_type.value,
                "evidence_count": len(evidence_list),
            },
        )
        return {**workflow_state, "payload": analysis_result}

    def finish_node(self, workflow_state: ResearchWorkflowState) -> ResearchWorkflowState:
        """
        Function Function:

            Finalize workflow run.
        """

        self._assert_not_cancelled(workflow_state["run_id"])
        self._update_run(
            workflow_state["run_id"],
            RunStage.DONE,
            {
                "action": workflow_state.get("action"),
                "query": workflow_state.get("query"),
                "paper_id_list": workflow_state.get("paper_id_list", []),
                "cluster_id_list": workflow_state.get("cluster_id_list", []),
            },
            status=RunStatus.DONE,
            message="Workflow completed successfully.",
        )
        self._checkpoint_run(
            workflow_state=workflow_state,
            stage=RunStage.DONE,
            checkpoint_payload={
                "action": workflow_state.get("action"),
                "paper_id_list": workflow_state.get("paper_id_list", []),
                "cluster_id_list": workflow_state.get("cluster_id_list", []),
            },
        )
        final_payload = workflow_state.get("payload")
        if final_payload is not None:
            self.runtime_store.write_text_artifact(
                project_id=workflow_state["project_id"],
                run_id=workflow_state["run_id"],
                relative_path="final.md",
                content=self._final_payload_to_markdown(final_payload),
            )
        return {"payload": workflow_state.get("payload")}

    def _final_payload_to_markdown(self, payload) -> str:
        if hasattr(payload, "content_md"):
            return str(payload.content_md)
        if isinstance(payload, list):
            line_list = ["# Final Result", ""]
            for item in payload:
                if hasattr(item, "label"):
                    line_list.append(f"- {getattr(item, 'label')}")
                elif hasattr(item, "title"):
                    line_list.append(f"- {getattr(item, 'title')}")
                else:
                    line_list.append(f"- {item}")
            return "\n".join(line_list)
        if hasattr(payload, "model_dump"):
            return "```json\n" + json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n```"
        return str(payload)

    def _resolve_resume_route(self, workflow_state: ResearchWorkflowState) -> str:
        """
        Function Function:

            Route workflow start from the latest persisted checkpoint.
        """

        action = workflow_state.get("action")
        resume_from_stage = str(workflow_state.get("resume_from_stage", ""))

        if resume_from_stage == RunStage.SEARCHING.value:
            if action == "research_workflow":
                return "ensure_index"
            return "finish"
        if resume_from_stage == RunStage.SYNCING_LIBRARY.value:
            return "finish"
        if resume_from_stage in {RunStage.PARSING.value, RunStage.INDEXING.value}:
            if action == "ask":
                return "qa"
            if action == "cluster":
                return "cluster"
            if action == "review":
                return "review"
            if action == "research_workflow":
                if workflow_state.get("cluster", True):
                    return "cluster"
                if workflow_state.get("review", True):
                    return "review"
            return "finish"
        if resume_from_stage == RunStage.CLUSTERING.value:
            if action in {"review", "research_workflow"} and workflow_state.get("review", True):
                return "review"
            return "finish"
        if resume_from_stage == RunStage.ANALYZING.value:
            return "finish"
        if resume_from_stage == RunStage.DONE.value:
            return "finish"
        return self.route_start({**workflow_state, "resume_from_stage": ""})

    def _checkpoint_run(self, workflow_state: ResearchWorkflowState, stage: RunStage, checkpoint_payload: dict) -> None:
        """
        Function Function:

            Persist run-level stage checkpoint into DB payload and workspace artifacts.
        """

        self._assert_not_cancelled(workflow_state["run_id"])
        workflow_run = self.run_dao.get_run(workflow_state["run_id"])
        if workflow_run is None:
            return
        merged_payload = dict(workflow_run.state_payload or {})
        merged_payload["last_checkpoint_stage"] = stage.value
        merged_payload["last_checkpoint_at"] = datetime.now(timezone.utc).isoformat()
        merged_payload.update(self._sanitize_state_payload(checkpoint_payload))
        workflow_run.state_payload = merged_payload
        workflow_run.updated_at = datetime.now(timezone.utc)
        self.run_dao.upsert_run(workflow_run)
        self.runtime_store.write_checkpoint(
            project_id=workflow_state["project_id"],
            run_id=workflow_state["run_id"],
            stage=stage.value,
            payload=self._sanitize_state_payload(checkpoint_payload),
        )
        self.runtime_store.write_state(
            project_id=workflow_state["project_id"],
            run_id=workflow_state["run_id"],
            state_payload=merged_payload,
            stage=workflow_run.stage.value,
            status=workflow_run.status.value,
            lifecycle="RUNNING" if workflow_run.status == RunStatus.RUNNING else "SUCCEEDED",
            error=workflow_run.error,
        )

    def _update_run(
        self,
        run_id: str,
        stage: RunStage,
        state_payload: dict | ResearchWorkflowState | None = None,
        status: RunStatus = RunStatus.RUNNING,
        error: str | None = None,
        message: str = "",
    ) -> None:
        """
        Function Function:

            Update workflow run persistence.
        """

        workflow_run = self.run_dao.get_run(run_id)
        if workflow_run is None:
            return
        if workflow_run.state_payload.get("cancelled"):
            raise RuntimeError(f"Run cancelled: run_id={run_id}")
        merged_payload = dict(workflow_run.state_payload or {})
        merged_payload.update(self._sanitize_state_payload(state_payload or {}))
        workflow_run.stage = stage
        workflow_run.status = status
        workflow_run.state_payload = merged_payload
        workflow_run.error = error
        workflow_run.updated_at = datetime.now(timezone.utc)
        self.run_dao.upsert_run(workflow_run)
        lifecycle = "RUNNING"
        if status == RunStatus.DONE:
            lifecycle = "SUCCEEDED"
        elif status == RunStatus.FAILED:
            lifecycle = "FAILED"
        self.runtime_store.write_state(
            project_id=workflow_run.project_id,
            run_id=workflow_run.run_id,
            state_payload=merged_payload,
            stage=stage.value,
            status=status.value,
            lifecycle=lifecycle,
            error=error,
        )

        event_name = "run.stage_changed"
        if status == RunStatus.DONE:
            event_name = "run.completed"
        elif status == RunStatus.FAILED:
            event_name = "run.failed"

        self._emit_event(
            run_id=workflow_run.run_id,
            project_id=workflow_run.project_id,
            event_name=event_name,
            stage=stage,
            progress=self.STAGE_PROGRESS_MAP.get(stage),
            message=message or f"Workflow entered stage {stage.value}.",
            payload=merged_payload,
        )
        if self.STAGE_PROGRESS_MAP.get(stage) is not None and status == RunStatus.RUNNING:
            self._emit_event(
                run_id=workflow_run.run_id,
                project_id=workflow_run.project_id,
                event_name="run.progress",
                stage=stage,
                progress=self.STAGE_PROGRESS_MAP.get(stage),
                message=message or f"Workflow progress updated at stage {stage.value}.",
                payload={"stage": stage.value},
            )

    def _assert_not_cancelled(self, run_id: str) -> None:
        """
        Function Function:

            Check cancellation flag and abort workflow if run is cancelled.
        """

        workflow_run = self.run_dao.get_run(run_id)
        if workflow_run is None:
            raise RuntimeError(f"Unknown run_id={run_id}")
        if workflow_run.state_payload.get("cancelled"):
            raise RuntimeError(f"Run cancelled: run_id={run_id}")

    def _emit_event(
        self,
        run_id: str,
        project_id: str,
        event_name: str,
        stage: RunStage | None,
        progress: float | None,
        message: str,
        payload: dict | None = None,
    ) -> None:
        """
        Function Function:

            Persist one workflow event.
        """

        self.run_event_dao.insert_event(
            RunEvent(
                run_id=run_id,
                project_id=project_id,
                event_name=event_name,
                stage=stage,
                progress=progress,
                message=message,
                payload=self._sanitize_state_payload(payload or {}),
            )
        )

    def _sanitize_state_payload(self, payload: dict | ResearchWorkflowState) -> dict:
        """
        Function Function:

            Convert workflow payload to JSON-safe summary.
        """

        sanitized_payload: dict = {}
        for key, value in dict(payload).items():
            if key == "payload":
                sanitized_payload["payload_type"] = type(value).__name__
                if hasattr(value, "result_id"):
                    sanitized_payload["result_id"] = getattr(value, "result_id")
                elif isinstance(value, list):
                    sanitized_payload["payload_count"] = len(value)
                continue
            if hasattr(value, "model_dump"):
                sanitized_payload[key] = value.model_dump(mode="json")
            elif isinstance(value, list):
                sanitized_list = []
                for item in value[:20]:
                    if hasattr(item, "model_dump"):
                        sanitized_list.append(item.model_dump(mode="json"))
                    else:
                        sanitized_list.append(item)
                sanitized_payload[key] = sanitized_list
            else:
                sanitized_payload[key] = value
        return sanitized_payload


###################################################################################################
###################################################################################################
### End of file
