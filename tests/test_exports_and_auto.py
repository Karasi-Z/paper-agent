# -*- coding: utf-8 -*-

from pathlib import Path

from fastapi.testclient import TestClient

from paper_agent.config import AppConfig
from paper_agent.server import create_app


def _build_app(tmp_path: Path):
    config = AppConfig(data_dir=tmp_path / "data")
    app = create_app(config)
    return app, app.state.service


def test_export_formats_and_auto_route(tmp_path: Path) -> None:
    app, service = _build_app(tmp_path)
    project = service.create_project(name="export-auto", question="Summarize scientific rag routes")
    service.import_text_paper(
        project_id=project.project_id,
        title="Hybrid Retrieval for Scientific Agents",
        content=(
            "Scientific agents benefit from lexical retrieval, dense retrieval, and reranking. "
            "The system should export markdown, json, csv, and bibtex outputs."
        ),
        authors=["Alice", "Bob"],
        abstract="Hybrid retrieval and export support for scientific agents.",
    )
    service.build_index(project.project_id)

    with TestClient(app) as client:
        markdown_response = client.get(f"/api/projects/{project.project_id}/export", params={"format": "markdown"})
        json_response = client.get(f"/api/projects/{project.project_id}/export", params={"format": "json"})
        csv_response = client.get(f"/api/projects/{project.project_id}/export", params={"format": "csv"})
        bibtex_response = client.get(f"/api/projects/{project.project_id}/export", params={"format": "bibtex"})
        auto_response = client.post(
            f"/api/projects/{project.project_id}/auto",
            json={"query": "Please write a literature review comparing retrieval methods", "limit": 5},
        )

    assert markdown_response.status_code == 200
    assert "# export-auto" in markdown_response.text
    assert json_response.status_code == 200
    assert "\"project_id\"" in json_response.text
    assert csv_response.status_code == 200
    assert "paper_id,title,source" in csv_response.text
    assert bibtex_response.status_code == 200
    assert "@article{" in bibtex_response.text
    assert auto_response.status_code == 200
    payload = auto_response.json()
    assert payload["mode"] == "workflow"
    assert "content_md" in payload


def test_fts_chunk_search_returns_lexical_hits(tmp_path: Path) -> None:
    _, service = _build_app(tmp_path)
    project = service.create_project(name="fts-test", question="How does lexical retrieval work?")
    paper = service.import_text_paper(
        project_id=project.project_id,
        title="FTS Retrieval",
        content="Lexical retrieval with BM25 and FTS5 improves exact term recall for rare terminology.",
        abstract="FTS based retrieval.",
    )
    service.build_index(project.project_id)

    lexical_item_list = service.chunk_dao.search_project_chunks(project.project_id, "rare terminology BM25", limit=5)

    assert lexical_item_list
    assert lexical_item_list[0]["metadata"]["paper_id"] == paper.paper_id
