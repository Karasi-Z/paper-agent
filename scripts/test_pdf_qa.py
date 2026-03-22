#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = PROJECT_ROOT / "Package"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from paper_agent.config import AppConfig
from paper_agent.workflow.service import PaperAgentService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PDF parsing and QA against one local paper.")
    parser.add_argument("--pdf", required=True, help="Absolute or relative path to the target PDF.")
    parser.add_argument("--question", required=True, help="Question to ask about the paper.")
    parser.add_argument("--title", default=None, help="Optional title override.")
    parser.add_argument(
        "--data-dir",
        default=str(PROJECT_ROOT / ".paper_agent_script_data"),
        help="Directory for SQLite/Chroma/script artifacts.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Top-k evidence items for retrieval.")
    parser.add_argument(
        "--llm-provider",
        choices=["ollama", "none"],
        default="ollama",
        help="Use Ollama for generation or fallback heuristic mode.",
    )
    parser.add_argument("--llm-model", default="qwen3:8b", help="LLM model name when using Ollama.")
    parser.add_argument(
        "--embedding-provider",
        choices=["ollama", "hash"],
        default="ollama",
        help="Embedding backend.",
    )
    parser.add_argument("--embedding-model", default="qwen3-embedding:0.6b", help="Embedding model name when using Ollama.")
    parser.add_argument("--parser-backend", default="auto", choices=["auto", "basic", "docling", "grobid"])
    parser.add_argument("--ollama-base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--reset-data", action="store_true", help="Delete the script data dir before running.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    data_dir = Path(args.data_dir).expanduser().resolve()
    if args.reset_data and data_dir.exists():
        shutil.rmtree(data_dir)

    config = AppConfig(
        data_dir=data_dir,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        embedding_provider=args.embedding_provider,
        embedding_model=args.embedding_model,
        ollama_base_url=args.ollama_base_url,
        parser_backend=args.parser_backend,
    )

    service = PaperAgentService(config)
    project = service.create_project(name="script-pdf-qa", question=args.question)
    paper = service.import_file_paper(project.project_id, str(pdf_path), title=args.title)
    service.build_index(project.project_id)
    result = service.ask(project.project_id, args.question, top_k=args.top_k)
    analysis = result.payload

    print(f"Project ID: {project.project_id}")
    print(f"Paper ID: {paper.paper_id}")
    print(f"Title: {paper.title}")
    if paper.abstract:
        print(f"Abstract: {paper.abstract[:400]}")
    print("\nAnswer:\n")
    print(analysis.content_md if analysis is not None else "No analysis result returned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
