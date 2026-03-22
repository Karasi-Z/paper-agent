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

This module implements local LLM client utilities for Paper Agent.

The module provides:

- heuristic text generation fallback
- Ollama connectivity check
- simplified local generation call

Description of Class and Function
--------------------------------
(1) HeuristicTextGenerationClient
    - Non-LLM fallback text generator

(2) OllamaTextGenerationClient
    - Lightweight Ollama generation client
"""


from typing import Sequence

try:
    import ollama
except Exception:  # pragma: no cover
    ollama = None


class HeuristicTextGenerationClient:
    """
    HeuristicTextGenerationClient
    -----------------------------
    Rule-based local fallback text generator.
    """

    def generate_markdown(self, title: str, bullet_points: Sequence[str]) -> str:
        """
        Function Function:

            Generate Markdown from bullet points.
        """

        markdown_line_list = [f"# {title}", ""]
        for item in bullet_points:
            markdown_line_list.append(f"- {item}")
        return "\n".join(markdown_line_list)


class OllamaTextGenerationClient:
    """
    OllamaTextGenerationClient
    --------------------------
    Simple Ollama generation wrapper.
    """

    def __init__(self, host: str, model: str) -> None:
        """
        Function Function:

            Initialize Ollama generation client.
        """

        self.host = host
        self.model = model

    def is_available(self) -> bool:
        """
        Function Function:

            Check whether Ollama client is importable and reachable.
        """

        if ollama is None:
            return False
        try:
            client = ollama.Client(host=self.host)
            client.ps()
            return True
        except Exception:
            return False

    def generate(self, prompt: str) -> str:
        """
        Function Function:

            Generate text from Ollama.
        """

        if ollama is None:
            raise RuntimeError("ollama package is not available")
        client = ollama.Client(host=self.host)
        response = client.generate(model=self.model, prompt=prompt)
        return response.get("response", "")


###################################################################################################
###################################################################################################
### End of file
