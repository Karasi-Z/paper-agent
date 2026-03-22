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

This module implements the local Gradio research workspace for
Paper Agent.

The interface follows the design document interaction modes:

- Auto mode
- Chat mode
- Research workflow mode
- Workspace mode
"""


import json

import gradio as gr

from paper_agent.config import AppConfig
from paper_agent.workflow.service import PaperAgentService


def create_gradio_app(config: AppConfig | None = None):
    """
    Function Function:

        Create Gradio research workspace application.
    """

    service = PaperAgentService(config)

    def _project_choices() -> list[tuple[str, str]]:
        """
        Function Function:

            Build project dropdown choices.
        """

        return [
            (f"{item.name} | {item.project_id}", item.project_id)
            for item in service.list_projects()
        ]

    def _project_update(project_id: str | None = None):
        """
        Function Function:

            Build Gradio dropdown update payload.
        """

        choice_list = _project_choices()
        value_list = [value for _, value in choice_list]
        selected_value = project_id if project_id in value_list else (value_list[0] if value_list else None)
        return gr.update(choices=choice_list, value=selected_value)

    def _snapshot_markdown(project_id: str | None) -> str:
        """
        Function Function:

            Build project snapshot Markdown view.
        """

        if not project_id:
            return "No project selected."

        snapshot = service.get_project_snapshot(project_id)
        line_list = [
            f"# {snapshot.project.name}",
            "",
            f"Project ID: `{snapshot.project.project_id}`",
            "",
            "## Question",
            snapshot.project.question,
            "",
            f"## Papers ({len(snapshot.papers)})",
        ]
        for item in snapshot.papers:
            source_text = item.source_key or item.paper_id
            line_list.append(f"- {item.title} | source={item.source} | key={source_text}")
        line_list.extend(["", f"## Analyses ({len(snapshot.analyses)})"])
        for item in snapshot.analyses[-3:]:
            line_list.append(f"- {item.task_type.value} | {item.result_id}")
        return "\n".join(line_list)

    def create_project_action(name: str, question: str):
        """
        Function Function:

            Create project and refresh UI state.
        """

        project = service.create_project(name=name, question=question)
        update_payload = _project_update(project.project_id)
        snapshot_text = _snapshot_markdown(project.project_id)
        return (
            update_payload,
            update_payload,
            update_payload,
            update_payload,
            snapshot_text,
            f"Created project `{project.project_id}`.",
        )

    def refresh_projects_action(project_id: str | None):
        """
        Function Function:

            Refresh project dropdowns and workspace snapshot.
        """

        update_payload = _project_update(project_id)
        selected_project_id = update_payload.get("value")
        snapshot_text = _snapshot_markdown(selected_project_id)
        return update_payload, update_payload, update_payload, update_payload, snapshot_text

    def show_snapshot_action(project_id: str | None):
        """
        Function Function:

            Render workspace snapshot and export Markdown.
        """

        if not project_id:
            return "No project selected.", ""
        return _snapshot_markdown(project_id), service.export_project_markdown(project_id)

    def import_text_action(project_id: str, title: str, content: str, authors_text: str, abstract: str):
        """
        Function Function:

            Import raw text paper through UI.
        """

        authors = [item.strip() for item in authors_text.split(",") if item.strip()]
        paper = service.import_text_paper(
            project_id=project_id,
            title=title,
            content=content,
            authors=authors,
            abstract=abstract,
        )
        return _snapshot_markdown(project_id), f"Imported paper `{paper.paper_id}`."

    def sync_library_action(
        project_id: str,
        provider: str,
        library_path: str,
        collection_id: str,
        mode: str,
        library_type: str,
        library_id: str,
        api_key: str,
        base_url: str,
    ):
        """
        Function Function:

            Sync literature manager data through UI.
        """

        operation = service.sync_library(
            project_id=project_id,
            provider=provider,
            library_path=library_path,
            collection_id=collection_id or None,
            library_options={
                key: value
                for key, value in {
                    "mode": mode or None,
                    "library_type": library_type or None,
                    "library_id": library_id or None,
                    "api_key": api_key or None,
                    "base_url": base_url or None,
                }.items()
                if value is not None
            },
        )
        return _snapshot_markdown(project_id), json.dumps(
            {"run_id": operation.run.run_id, "paper_count": len(operation.payload or [])},
            ensure_ascii=False,
            indent=2,
        )

    def ask_action(project_id: str, query: str, top_k: int):
        """
        Function Function:

            Execute chat-style QA through UI.
        """

        operation = service.ask(project_id=project_id, query=query, top_k=top_k)
        return operation.payload.content_md

    def run_workflow_action(project_id: str, query: str, limit: int):
        """
        Function Function:

            Execute research workflow through UI.
        """

        operation = service.run_research_workflow(project_id=project_id, query=query, limit=limit)
        return operation.payload.content_md

    def auto_action(project_id: str, query: str, limit: int, top_k: int):
        """
        Function Function:

            Route one request through the unified auto entry.
        """

        result = service.run_auto(project_id=project_id, query=query, limit=limit, top_k=top_k)
        route_text = f"Mode: `{result['mode']}`\n\nReason: {result['rationale']}"
        if result.get("run_id"):
            route_text += f"\n\nRun ID: `{result['run_id']}`"
        return route_text, result["content_md"]

    def push_note_action(
        project_id: str,
        provider: str,
        library_path: str,
        paper_id: str,
        item_id: str,
        note_md: str,
        result_id: str,
        prefer_task_type: str,
        mode: str,
        library_type: str,
        library_id: str,
        api_key: str,
        base_url: str,
    ):
        """
        Function Function:

            Push note through UI to literature manager backend.
        """

        result = service.push_note_to_library(
            project_id=project_id,
            provider=provider,
            library_path=library_path,
            paper_id=paper_id or None,
            item_id=item_id or None,
            note_md=note_md or None,
            result_id=result_id or None,
            prefer_task_type=prefer_task_type or None,
            library_options={
                key: value
                for key, value in {
                    "mode": mode or None,
                    "library_type": library_type or None,
                    "library_id": library_id or None,
                    "api_key": api_key or None,
                    "base_url": base_url or None,
                }.items()
                if value is not None
            },
        )
        return json.dumps(result, ensure_ascii=False, indent=2)

    with gr.Blocks(title="Paper Agent Research Workspace") as demo:
        gr.Markdown(
            """
            # Paper Agent

            Local-first research workspace with auto, chat, workflow, and workspace modes.
            """
        )

        with gr.Tab("Auto"):
            auto_project = gr.Dropdown(label="Project", choices=_project_choices())
            auto_query = gr.Textbox(label="Task or Question", lines=4)
            with gr.Row():
                auto_limit = gr.Slider(label="Workflow Search Limit", minimum=1, maximum=20, step=1, value=10)
                auto_top_k = gr.Slider(label="Chat Top K", minimum=1, maximum=10, step=1, value=5)
            auto_button = gr.Button("Run Auto", variant="primary")
            auto_route = gr.Markdown()
            auto_result = gr.Markdown()

        with gr.Tab("Workspace"):
            with gr.Row():
                create_name = gr.Textbox(label="Project Name")
                create_question = gr.Textbox(label="Research Question")
            with gr.Row():
                create_button = gr.Button("Create Project", variant="primary")
                refresh_button = gr.Button("Refresh Projects")
            workspace_project = gr.Dropdown(label="Project", choices=_project_choices())
            workspace_status = gr.Textbox(label="Workspace Status")
            workspace_snapshot = gr.Markdown(value="No project selected.")
            workspace_export = gr.Markdown()

            gr.Markdown("## Import Text Paper")
            import_title = gr.Textbox(label="Paper Title")
            import_authors = gr.Textbox(label="Authors (comma separated)")
            import_abstract = gr.Textbox(label="Abstract")
            import_content = gr.Textbox(label="Paper Content", lines=10)
            import_button = gr.Button("Import Text")

            gr.Markdown("## Sync Literature Manager")
            with gr.Row():
                sync_provider = gr.Dropdown(
                    label="Provider",
                    choices=["zotero", "mendeley", "endnote"],
                    value="zotero",
                )
                sync_library_path = gr.Textbox(label="Library Path", value="")
                sync_collection_id = gr.Textbox(label="Collection ID", value="")
            with gr.Row():
                sync_mode = gr.Textbox(label="Mode", value="")
                sync_library_type = gr.Textbox(label="Library Type", value="users")
                sync_library_id = gr.Textbox(label="Library ID", value="")
            with gr.Row():
                sync_api_key = gr.Textbox(label="API Key", type="password", value="")
                sync_base_url = gr.Textbox(label="Base URL", value="https://api.zotero.org")
            sync_button = gr.Button("Sync Library")
            sync_result = gr.Code(label="Sync Result", language="json")

            gr.Markdown("## Push Analysis Note")
            with gr.Row():
                note_provider = gr.Dropdown(
                    label="Provider",
                    choices=["zotero", "mendeley", "endnote"],
                    value="zotero",
                )
                note_library_path = gr.Textbox(label="Library Path", value="")
            with gr.Row():
                note_paper_id = gr.Textbox(label="Paper ID", value="")
                note_item_id = gr.Textbox(label="Item ID", value="")
                note_result_id = gr.Textbox(label="Result ID", value="")
            with gr.Row():
                note_prefer_task_type = gr.Textbox(label="Prefer Task Type", value="review")
                note_mode = gr.Textbox(label="Mode", value="")
                note_library_type = gr.Textbox(label="Library Type", value="users")
                note_library_id = gr.Textbox(label="Library ID", value="")
            with gr.Row():
                note_api_key = gr.Textbox(label="API Key", type="password", value="")
                note_base_url = gr.Textbox(label="Base URL", value="https://api.zotero.org")
            note_md = gr.Textbox(label="Manual Note Markdown (optional)", lines=8)
            push_note_button = gr.Button("Push Note")
            push_note_result = gr.Code(label="Push Note Result", language="json")

        with gr.Tab("Chat"):
            chat_project = gr.Dropdown(label="Project", choices=_project_choices())
            chat_query = gr.Textbox(label="Question", lines=4)
            chat_top_k = gr.Slider(label="Top K", minimum=1, maximum=10, step=1, value=5)
            chat_button = gr.Button("Ask", variant="primary")
            chat_answer = gr.Markdown()

        with gr.Tab("Workflow"):
            workflow_project = gr.Dropdown(label="Project", choices=_project_choices())
            workflow_query = gr.Textbox(label="Research Query", lines=4)
            workflow_limit = gr.Slider(label="Search Limit", minimum=1, maximum=20, step=1, value=10)
            workflow_button = gr.Button("Run Research Workflow", variant="primary")
            workflow_result = gr.Markdown()

        create_button.click(
            create_project_action,
            inputs=[create_name, create_question],
            outputs=[auto_project, workspace_project, chat_project, workflow_project, workspace_snapshot, workspace_status],
        )
        refresh_button.click(
            refresh_projects_action,
            inputs=[workspace_project],
            outputs=[auto_project, workspace_project, chat_project, workflow_project, workspace_snapshot],
        )
        workspace_project.change(
            show_snapshot_action,
            inputs=[workspace_project],
            outputs=[workspace_snapshot, workspace_export],
        )
        import_button.click(
            import_text_action,
            inputs=[workspace_project, import_title, import_content, import_authors, import_abstract],
            outputs=[workspace_snapshot, workspace_status],
        )
        sync_button.click(
            sync_library_action,
            inputs=[
                workspace_project,
                sync_provider,
                sync_library_path,
                sync_collection_id,
                sync_mode,
                sync_library_type,
                sync_library_id,
                sync_api_key,
                sync_base_url,
            ],
            outputs=[workspace_snapshot, sync_result],
        )
        push_note_button.click(
            push_note_action,
            inputs=[
                workspace_project,
                note_provider,
                note_library_path,
                note_paper_id,
                note_item_id,
                note_md,
                note_result_id,
                note_prefer_task_type,
                note_mode,
                note_library_type,
                note_library_id,
                note_api_key,
                note_base_url,
            ],
            outputs=[push_note_result],
        )
        chat_button.click(
            ask_action,
            inputs=[chat_project, chat_query, chat_top_k],
            outputs=[chat_answer],
        )
        workflow_button.click(
            run_workflow_action,
            inputs=[workflow_project, workflow_query, workflow_limit],
            outputs=[workflow_result],
        )
        auto_button.click(
            auto_action,
            inputs=[auto_project, auto_query, auto_limit, auto_top_k],
            outputs=[auto_route, auto_result],
        )

    return demo


###################################################################################################
###################################################################################################
### End of file
