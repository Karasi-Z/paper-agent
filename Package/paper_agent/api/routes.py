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

This module implements FastAPI routes for Paper Agent.
"""


from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import PlainTextResponse, Response, StreamingResponse

from paper_agent.api.deps import get_service
from paper_agent.api.sse import build_run_event_stream
from paper_agent.models.schemas import (
    AskRequest,
    AutoRouteRequest,
    CreateProjectRequest,
    ImportFileRequest,
    ImportTextRequest,
    LibrarySyncRequest,
    PushNoteRequest,
    ResearchWorkflowRequest,
    SearchRequest,
)
from paper_agent.workflow.service import PaperAgentService


router = APIRouter()


@router.get("/health")
def health() -> dict:
    """
    Function Function:

        Health check endpoint.
    """

    return {"status": "ok"}


@router.post("/api/projects")
def create_project(request: CreateProjectRequest, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Create project endpoint.
    """

    return service.create_project(
        name=request.name,
        question=request.question,
        mode=request.mode,
        settings=request.settings,
    )


@router.get("/api/projects/{project_id}")
def get_project(project_id: str, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Project snapshot endpoint.
    """

    try:
        return service.get_project_snapshot(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/projects/{project_id}/search")
def search_and_add(project_id: str, request: SearchRequest, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Search and attach papers endpoint.
    """

    return _encode_operation(
        service.search_and_add(
            project_id=project_id,
            query=request.query,
            limit=request.limit,
            author=request.author,
            categories=request.categories,
            from_year=request.from_year,
            to_year=request.to_year,
        )
    )


@router.post("/api/projects/{project_id}/workflow/research")
def run_research_workflow(project_id: str, request: ResearchWorkflowRequest, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        End-to-end research workflow endpoint.
    """

    if not request.query:
        raise HTTPException(status_code=400, detail="query is required for research workflow")
    return _encode_operation(
        service.run_research_workflow(
            project_id=project_id,
            query=request.query,
            limit=request.limit,
            review=request.review,
            cluster=request.cluster,
            author=request.author,
            categories=request.categories,
            from_year=request.from_year,
            to_year=request.to_year,
        )
    )


@router.post("/api/projects/{project_id}/import/text")
def import_text(project_id: str, request: ImportTextRequest, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Raw text import endpoint.
    """

    return service.import_text_paper(
        project_id=project_id,
        title=request.title,
        content=request.content,
        authors=request.authors,
        abstract=request.abstract,
        tags=request.tags,
    )


@router.post("/api/projects/{project_id}/import/file")
def import_file(project_id: str, request: ImportFileRequest, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        File import endpoint.
    """

    try:
        return service.import_file_paper(project_id=project_id, path=request.path, title=request.title)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/projects/{project_id}/library/sync")
def sync_library(project_id: str, request: LibrarySyncRequest, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Literature manager synchronization endpoint.
    """

    return _encode_operation(
        service.sync_library(
            project_id=project_id,
            provider=request.provider,
            library_path=request.library_path,
            collection_id=request.collection_id,
            library_options={
                key: value
                for key, value in {
                    "mode": request.mode,
                    "library_type": request.library_type,
                    "library_id": request.library_id,
                    "api_key": request.api_key,
                    "base_url": request.base_url,
                }.items()
                if value is not None
            },
        )
    )


@router.post("/api/projects/{project_id}/library/push-note")
def push_note(project_id: str, request: PushNoteRequest, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Literature manager note push endpoint.
    """

    try:
        return service.push_note_to_library(
            project_id=project_id,
            provider=request.provider,
            library_path=request.library_path,
            paper_id=request.paper_id,
            item_id=request.item_id,
            note_md=request.note_md,
            result_id=request.result_id,
            prefer_task_type=request.prefer_task_type,
            library_options={
                key: value
                for key, value in {
                    "mode": request.mode,
                    "library_type": request.library_type,
                    "library_id": request.library_id,
                    "api_key": request.api_key,
                    "base_url": request.base_url,
                }.items()
                if value is not None
            },
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/projects/{project_id}/index")
def build_index(project_id: str, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Build index endpoint.
    """

    return _encode_operation(service.build_index(project_id))


@router.post("/api/projects/{project_id}/ask")
def ask(project_id: str, request: AskRequest, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Ask question endpoint.
    """

    return _encode_operation(service.ask(project_id=project_id, query=request.query, top_k=request.top_k))


@router.post("/api/projects/{project_id}/auto")
def auto_route(project_id: str, request: AutoRouteRequest, service: PaperAgentService = Depends(get_service)):
    """
    Auto-route endpoint.
    """

    return service.run_auto(project_id=project_id, query=request.query, limit=request.limit, top_k=request.top_k)


@router.post("/api/projects/{project_id}/cluster")
def cluster(project_id: str, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Cluster endpoint.
    """

    return _encode_operation(service.cluster_project(project_id))


@router.post("/api/projects/{project_id}/review")
def review(project_id: str, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Review endpoint.
    """

    return _encode_operation(service.generate_review(project_id))


@router.get("/api/projects/{project_id}/export")
def export_markdown(
    project_id: str,
    format: str = Query(default="markdown"),
    service: PaperAgentService = Depends(get_service),
):
    """
    Function Function:

        Markdown export endpoint.
    """

    try:
        content = service.export_project(project_id, fmt=format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized_format = format.lower()
    media_type = "text/markdown; charset=utf-8"
    if normalized_format == "json":
        media_type = "application/json"
    elif normalized_format == "csv":
        media_type = "text/csv; charset=utf-8"
    elif normalized_format in {"bib", "bibtex"}:
        media_type = "application/x-bibtex; charset=utf-8"

    if normalized_format in {"md", "markdown"}:
        return PlainTextResponse(content)
    return Response(content=content, media_type=media_type)


@router.get("/api/runs/{run_id}")
def get_run(run_id: str, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Workflow run query endpoint.
    """

    workflow_run = service.get_run(run_id)
    if workflow_run is None:
        raise HTTPException(status_code=404, detail=f"Unknown run_id={run_id}")
    return workflow_run


@router.post("/api/runs/{run_id}/resume")
def resume_run(run_id: str, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Workflow run resume endpoint.
    """

    try:
        return _encode_operation(service.resume_run(run_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/cancel")
def cancel_run(run_id: str, reason: str = "Cancelled by user", service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Workflow run cancel endpoint.
    """

    try:
        return service.cancel_run(run_id=run_id, reason=reason)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/runs/{run_id}/events")
def get_run_events(run_id: str, service: PaperAgentService = Depends(get_service)):
    """
    Function Function:

        Workflow run SSE endpoint.
    """

    workflow_run = service.get_run(run_id)
    if workflow_run is None:
        raise HTTPException(status_code=404, detail=f"Unknown run_id={run_id}")
    run_event_list = service.get_run_events(run_id)
    return StreamingResponse(build_run_event_stream(run_event_list), media_type="text/event-stream")


def _encode_operation(operation_result) -> dict:
    """
    Function Function:

        Encode operation result to JSON-safe payload.
    """

    return {
        "run": jsonable_encoder(operation_result.run),
        "payload": jsonable_encoder(operation_result.payload),
    }


###################################################################################################
###################################################################################################
### End of file
