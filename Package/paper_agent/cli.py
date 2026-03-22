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

This module implements the CLI entry for Paper Agent.
"""


import argparse
import inspect
import json
import subprocess
import sys
from pathlib import Path

import uvicorn

from paper_agent.config import AppConfig
from paper_agent.server import create_app
from paper_agent.workflow.service import PaperAgentService


def build_parser() -> argparse.ArgumentParser:
    """
    Function Function:

        Build command-line parser.
    """

    parser = argparse.ArgumentParser(prog="paper-agent")
    parser.add_argument("--data-dir", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    create_project = subparsers.add_parser("create-project")
    create_project.add_argument("--name", required=True)
    create_project.add_argument("--question", required=True)

    import_text = subparsers.add_parser("import-text")
    import_text.add_argument("--project-id", required=True)
    import_text.add_argument("--title", required=True)
    import_text.add_argument("--file", required=True)

    search_add = subparsers.add_parser("search-add")
    search_add.add_argument("--project-id", required=True)
    search_add.add_argument("--query", required=True)
    search_add.add_argument("--limit", type=int, default=10)
    search_add.add_argument("--author", default=None)
    search_add.add_argument("--category", action="append", dest="categories", default=[])
    search_add.add_argument("--from-year", type=int, default=None)
    search_add.add_argument("--to-year", type=int, default=None)

    workflow = subparsers.add_parser("research-workflow")
    workflow.add_argument("--project-id", required=True)
    workflow.add_argument("--query", required=True)
    workflow.add_argument("--limit", type=int, default=10)
    workflow.add_argument("--no-review", action="store_true")
    workflow.add_argument("--no-cluster", action="store_true")
    workflow.add_argument("--author", default=None)
    workflow.add_argument("--category", action="append", dest="categories", default=[])
    workflow.add_argument("--from-year", type=int, default=None)
    workflow.add_argument("--to-year", type=int, default=None)

    push_note = subparsers.add_parser("push-note")
    push_note.add_argument("--project-id", required=True)
    push_note.add_argument("--provider", required=True)
    push_note.add_argument("--library-path", default="")
    push_note.add_argument("--paper-id", default=None)
    push_note.add_argument("--item-id", default=None)
    push_note.add_argument("--note-file", default=None)
    push_note.add_argument("--result-id", default=None)
    push_note.add_argument("--prefer-task-type", default="review")
    push_note.add_argument("--mode", default=None)
    push_note.add_argument("--library-type", default=None)
    push_note.add_argument("--library-id", default=None)
    push_note.add_argument("--api-key", default=None)
    push_note.add_argument("--base-url", default=None)

    build_index = subparsers.add_parser("build-index")
    build_index.add_argument("--project-id", required=True)

    ui = subparsers.add_parser("ui")
    ui.add_argument("--host", default="127.0.0.1")
    ui.add_argument("--port", type=int, default=7860)
    ui.add_argument("--inbrowser", action="store_true")

    ask = subparsers.add_parser("ask")
    ask.add_argument("--project-id", required=True)
    ask.add_argument("--query", required=True)
    ask.add_argument("--top-k", type=int, default=5)

    cluster = subparsers.add_parser("cluster")
    cluster.add_argument("--project-id", required=True)

    review = subparsers.add_parser("review")
    review.add_argument("--project-id", required=True)

    resume_run = subparsers.add_parser("resume-run")
    resume_run.add_argument("--run-id", required=True)

    export = subparsers.add_parser("export")
    export.add_argument("--project-id", required=True)
    export.add_argument("--format", default="markdown", choices=["markdown", "json", "csv", "bibtex"])

    auto = subparsers.add_parser("auto")
    auto.add_argument("--project-id", required=True)
    auto.add_argument("--query", default="")
    auto.add_argument("--limit", type=int, default=10)
    auto.add_argument("--top-k", type=int, default=5)

    run = subparsers.add_parser("run")
    run_subparsers = run.add_subparsers(dest="run_command", required=True)

    run_start = run_subparsers.add_parser("start")
    run_start.add_argument("--project-id", required=True)
    run_start.add_argument(
        "--task",
        required=True,
        choices=["search", "index", "ask", "cluster", "review", "workflow", "sync-library"],
    )
    run_start.add_argument("--query", default=None)
    run_start.add_argument("--limit", type=int, default=10)
    run_start.add_argument("--top-k", type=int, default=5)
    run_start.add_argument("--author", default=None)
    run_start.add_argument("--category", action="append", dest="categories", default=[])
    run_start.add_argument("--from-year", type=int, default=None)
    run_start.add_argument("--to-year", type=int, default=None)
    run_start.add_argument("--no-review", action="store_true")
    run_start.add_argument("--no-cluster", action="store_true")
    run_start.add_argument("--provider", default="zotero")
    run_start.add_argument("--library-path", default="")
    run_start.add_argument("--collection-id", default=None)
    run_start.add_argument("--async", dest="async_mode", action="store_true")

    run_status = run_subparsers.add_parser("status")
    run_status.add_argument("--run-id", required=True)

    run_logs = run_subparsers.add_parser("logs")
    run_logs.add_argument("--run-id", required=True)
    run_logs.add_argument("--tail", type=int, default=20)

    run_resume = run_subparsers.add_parser("resume")
    run_resume.add_argument("--run-id", required=True)

    run_cancel = run_subparsers.add_parser("cancel")
    run_cancel.add_argument("--run-id", required=True)
    run_cancel.add_argument("--reason", default="Cancelled by user")

    run_worker = run_subparsers.add_parser("_worker", help=argparse.SUPPRESS)
    run_worker.add_argument("--run-id", required=True)

    return parser


def main() -> None:
    """
    Function Function:

        Execute CLI command.
    """

    parser = build_parser()
    args = parser.parse_args()
    config = AppConfig(data_dir=Path(args.data_dir)) if args.data_dir else AppConfig.from_env()

    if args.command == "serve":
        uvicorn.run(create_app(config), host=args.host, port=args.port, reload=args.reload)
        return
    if args.command == "ui":
        from paper_agent.ui.gradio_app import create_gradio_app

        demo = create_gradio_app(config)
        launch_kwargs = {
            "server_name": args.host,
            "server_port": args.port,
            "inbrowser": args.inbrowser,
        }
        if "show_api" in inspect.signature(demo.launch).parameters:
            launch_kwargs["show_api"] = False
        last_error = None
        for port in range(args.port, args.port + 10):
            try:
                launch_kwargs["server_port"] = port
                demo.launch(**launch_kwargs)
                return
            except OSError as exc:
                last_error = exc
                if "Cannot find empty port" not in str(exc):
                    raise
        if last_error is not None:
            raise last_error
        return

    service = PaperAgentService(config)
    if args.command == "create-project":
        print_json(service.create_project(name=args.name, question=args.question).model_dump(mode="json"))
    elif args.command == "import-text":
        content = Path(args.file).read_text(encoding="utf-8")
        print_json(
            service.import_text_paper(
                project_id=args.project_id,
                title=args.title,
                content=content,
            ).model_dump(mode="json")
        )
    elif args.command == "search-add":
        print_json(
            _operation_dump(
                service.search_and_add(
                    args.project_id,
                    args.query,
                    args.limit,
                    author=args.author,
                    categories=args.categories,
                    from_year=args.from_year,
                    to_year=args.to_year,
                )
            )
        )
    elif args.command == "research-workflow":
        print_json(
            _operation_dump(
                service.run_research_workflow(
                    args.project_id,
                    args.query,
                    args.limit,
                    review=not args.no_review,
                    cluster=not args.no_cluster,
                    author=args.author,
                    categories=args.categories,
                    from_year=args.from_year,
                    to_year=args.to_year,
                )
            )
        )
    elif args.command == "push-note":
        note_md = Path(args.note_file).read_text(encoding="utf-8") if args.note_file else None
        print_json(
            service.push_note_to_library(
                project_id=args.project_id,
                provider=args.provider,
                library_path=args.library_path,
                paper_id=args.paper_id,
                item_id=args.item_id,
                note_md=note_md,
                result_id=args.result_id,
                prefer_task_type=args.prefer_task_type,
                library_options={
                    key: value
                    for key, value in {
                        "mode": args.mode,
                        "library_type": args.library_type,
                        "library_id": args.library_id,
                        "api_key": args.api_key,
                        "base_url": args.base_url,
                    }.items()
                    if value is not None
                },
            )
        )
    elif args.command == "build-index":
        print_json(_operation_dump(service.build_index(args.project_id)))
    elif args.command == "ask":
        print_json(_operation_dump(service.ask(args.project_id, args.query, args.top_k)))
    elif args.command == "cluster":
        print_json(_operation_dump(service.cluster_project(args.project_id)))
    elif args.command == "review":
        print_json(_operation_dump(service.generate_review(args.project_id)))
    elif args.command == "resume-run":
        print_json(_operation_dump(service.resume_run(args.run_id)))
    elif args.command == "run":
        if args.run_command == "start":
            try:
                if args.async_mode:
                    action, task_kwargs = _resolve_run_task_args(args)
                    workflow_run = service.create_run(project_id=args.project_id, action=action, **task_kwargs)
                    worker_pid, log_path = _spawn_async_worker(config, workflow_run.run_id)
                    print_json(
                        {
                            "run": workflow_run.model_dump(mode="json"),
                            "worker_pid": worker_pid,
                            "worker_log_path": str(log_path),
                        }
                    )
                else:
                    print_json(_operation_dump(_run_start(service, args)))
            except ValueError as exc:
                parser.error(str(exc))
        elif args.run_command == "status":
            workflow_run = service.get_run(args.run_id)
            if workflow_run is None:
                parser.error(f"Unknown run_id: {args.run_id}")
            event_count = len(service.get_run_events(args.run_id))
            print_json(
                {
                    "run": workflow_run.model_dump(mode="json"),
                    "event_count": event_count,
                    "last_checkpoint_stage": workflow_run.state_payload.get("last_checkpoint_stage"),
                    "last_checkpoint_at": workflow_run.state_payload.get("last_checkpoint_at"),
                }
            )
        elif args.run_command == "logs":
            workflow_run = service.get_run(args.run_id)
            if workflow_run is None:
                parser.error(f"Unknown run_id: {args.run_id}")
            run_event_list = service.get_run_events(args.run_id)
            tail = max(1, args.tail)
            print_json(
                {
                    "run_id": args.run_id,
                    "events": [item.model_dump(mode="json") for item in run_event_list[-tail:]],
                }
            )
        elif args.run_command == "resume":
            try:
                print_json(_operation_dump(service.resume_run(args.run_id)))
            except (KeyError, ValueError) as exc:
                parser.error(str(exc))
        elif args.run_command == "cancel":
            try:
                workflow_run = service.cancel_run(args.run_id, reason=args.reason)
            except KeyError:
                parser.error(f"Unknown run_id: {args.run_id}")
            print_json(workflow_run.model_dump(mode="json"))
        elif args.run_command == "_worker":
            try:
                _ = service.execute_run(args.run_id)
            except Exception as exc:
                print(json.dumps({"run_id": args.run_id, "error": str(exc)}, ensure_ascii=False))
                raise
        else:  # pragma: no cover
            parser.error(f"Unknown run subcommand: {args.run_command}")
    elif args.command == "export":
        print(service.export_project(args.project_id, fmt=args.format))
    elif args.command == "auto":
        print_json(service.run_auto(args.project_id, args.query, limit=args.limit, top_k=args.top_k))
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")


def _run_start(service: PaperAgentService, args) -> object:
    """
    Function Function:

        Execute one workflow task from unified `run start` command.
    """

    action, task_kwargs = _resolve_run_task_args(args)
    if action == "search_add":
        return service.search_and_add(project_id=args.project_id, **task_kwargs)
    if action == "build_index":
        return service.build_index(args.project_id)
    if action == "ask":
        return service.ask(args.project_id, task_kwargs["query"], task_kwargs["top_k"])
    if action == "cluster":
        return service.cluster_project(args.project_id)
    if action == "review":
        return service.generate_review(args.project_id)
    if action == "research_workflow":
        return service.run_research_workflow(
            project_id=args.project_id,
            **task_kwargs,
        )
    if action == "sync_library":
        return service.sync_library(
            project_id=args.project_id,
            **task_kwargs,
        )
    raise ValueError(f"Unsupported action: {action}")


def _resolve_run_task_args(args) -> tuple[str, dict]:
    """
    Function Function:

        Resolve run task to workflow action plus action kwargs.
    """

    if args.task == "search":
        if not args.query:
            raise ValueError("--query is required for task=search")
        return (
            "search_add",
            {
                "query": args.query,
                "limit": args.limit,
                "author": args.author,
                "categories": args.categories,
                "from_year": args.from_year,
                "to_year": args.to_year,
            },
        )
    if args.task == "index":
        return ("build_index", {})
    if args.task == "ask":
        if not args.query:
            raise ValueError("--query is required for task=ask")
        return ("ask", {"query": args.query, "top_k": args.top_k})
    if args.task == "cluster":
        return ("cluster", {})
    if args.task == "review":
        return ("review", {})
    if args.task == "workflow":
        if not args.query:
            raise ValueError("--query is required for task=workflow")
        return (
            "research_workflow",
            {
                "query": args.query,
                "limit": args.limit,
                "review": not args.no_review,
                "cluster": not args.no_cluster,
                "author": args.author,
                "categories": args.categories,
                "from_year": args.from_year,
                "to_year": args.to_year,
                "top_k": max(args.top_k, 10),
            },
        )
    if args.task == "sync-library":
        return (
            "sync_library",
            {
                "provider": args.provider,
                "library_path": args.library_path,
                "collection_id": args.collection_id,
                "library_options": {},
            },
        )
    raise ValueError(f"Unsupported task: {args.task}")


def _spawn_async_worker(config: AppConfig, run_id: str) -> tuple[int, Path]:
    """
    Function Function:

        Spawn detached worker subprocess for one workflow run.
    """

    python_bin = Path(sys.executable)
    log_dir = Path(config.data_dir) / "workspace" / "workers"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_id}.log"
    with log_path.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [
                str(python_bin),
                "-m",
                "paper_agent.cli",
                "--data-dir",
                str(config.data_dir),
                "run",
                "_worker",
                "--run-id",
                run_id,
            ],
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    return process.pid, log_path


def _operation_dump(result) -> dict:
    """
    Function Function:

        Convert operation result to JSON-safe dictionary.
    """

    payload = result.payload
    if isinstance(payload, list):
        payload = [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in payload]
    elif hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    return {
        "run": result.run.model_dump(mode="json"),
        "payload": payload,
    }


def print_json(payload: dict) -> None:
    """
    Function Function:

        Print JSON with UTF-8 safe formatting.
    """

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


###################################################################################################
###################################################################################################
### End of file
