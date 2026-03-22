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

This module implements the minimal Python SDK client for Paper Agent.
"""


import httpx

from paper_agent.models.entities import OperationResult, ProjectSnapshot, ResearchProject, WorkflowRun
from paper_agent.models.enums import ProjectMode


class PaperAgentClient:
    """
    PaperAgentClient
    ----------------
    Minimal synchronous SDK client for Paper Agent REST API.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 60.0,
        transport=None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Function Function:

            Initialize SDK HTTP client.
        """

        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
            headers=headers,
        )

    def close(self) -> None:
        """
        Function Function:

            Close underlying HTTP client.
        """

        self._client.close()

    def create_project(
        self,
        name: str,
        question: str,
        mode: ProjectMode | str = ProjectMode.WORKFLOW,
        settings: dict | None = None,
    ) -> ResearchProject:
        """
        Function Function:

            Create research project through REST API.
        """

        response = self._client.post(
            "/api/projects",
            json={
                "name": name,
                "question": question,
                "mode": mode.value if isinstance(mode, ProjectMode) else mode,
                "settings": settings or {},
            },
        )
        response.raise_for_status()
        return ResearchProject.model_validate(response.json())

    def get_project(self, project_id: str) -> ProjectSnapshot:
        """
        Function Function:

            Fetch project snapshot through REST API.
        """

        response = self._client.get(f"/api/projects/{project_id}")
        response.raise_for_status()
        return ProjectSnapshot.model_validate(response.json())

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

            Search ArXiv and attach results to one project.
        """

        response = self._client.post(
            f"/api/projects/{project_id}/search",
            json={
                "query": query,
                "limit": limit,
                "author": author,
                "categories": categories or [],
                "from_year": from_year,
                "to_year": to_year,
            },
        )
        response.raise_for_status()
        return OperationResult.model_validate(response.json())

    def build_index(self, project_id: str) -> OperationResult:
        """
        Function Function:

            Build project retrieval index.
        """

        response = self._client.post(f"/api/projects/{project_id}/index")
        response.raise_for_status()
        return OperationResult.model_validate(response.json())

    def ask(self, project_id: str, query: str, top_k: int = 5) -> OperationResult:
        """
        Function Function:

            Execute project-level question answering.
        """

        response = self._client.post(
            f"/api/projects/{project_id}/ask",
            json={"query": query, "top_k": top_k},
        )
        response.raise_for_status()
        return OperationResult.model_validate(response.json())

    def run_auto(self, project_id: str, query: str, limit: int = 10, top_k: int | None = None) -> dict:
        """
        Execute the auto-router entrypoint.
        """

        response = self._client.post(
            f"/api/projects/{project_id}/auto",
            json={"query": query, "limit": limit, "top_k": top_k},
        )
        response.raise_for_status()
        return response.json()

    def cluster_project(self, project_id: str) -> OperationResult:
        """
        Function Function:

            Execute project-level clustering.
        """

        response = self._client.post(f"/api/projects/{project_id}/cluster")
        response.raise_for_status()
        return OperationResult.model_validate(response.json())

    def generate_review(self, project_id: str) -> OperationResult:
        """
        Function Function:

            Generate research review for one project.
        """

        response = self._client.post(f"/api/projects/{project_id}/review")
        response.raise_for_status()
        return OperationResult.model_validate(response.json())

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

            Execute configurable research workflow.
        """

        response = self._client.post(
            f"/api/projects/{project_id}/workflow/research",
            json={
                "query": query,
                "limit": limit,
                "review": review,
                "cluster": cluster,
                "author": author,
                "categories": categories or [],
                "from_year": from_year,
                "to_year": to_year,
            },
        )
        response.raise_for_status()
        return OperationResult.model_validate(response.json())

    def get_run(self, run_id: str) -> WorkflowRun:
        """
        Function Function:

            Fetch workflow run status.
        """

        response = self._client.get(f"/api/runs/{run_id}")
        response.raise_for_status()
        return WorkflowRun.model_validate(response.json())

    def resume_run(self, run_id: str) -> OperationResult:
        """
        Function Function:

            Resume one workflow run.
        """

        response = self._client.post(f"/api/runs/{run_id}/resume")
        response.raise_for_status()
        return OperationResult.model_validate(response.json())

    def export_project_markdown(self, project_id: str) -> str:
        """
        Function Function:

            Export one project in Markdown format.
        """

        response = self._client.get(f"/api/projects/{project_id}/export", params={"format": "markdown"})
        response.raise_for_status()
        return response.text

    def export_project(self, project_id: str, fmt: str = "markdown") -> str:
        """
        Export one project with a specific format.
        """

        response = self._client.get(f"/api/projects/{project_id}/export", params={"format": fmt})
        response.raise_for_status()
        return response.text

    def __enter__(self) -> "PaperAgentClient":
        """
        Function Function:

            Enter context manager.
        """

        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Function Function:

            Exit context manager and close HTTP client.
        """

        self.close()


###################################################################################################
###################################################################################################
### End of file
