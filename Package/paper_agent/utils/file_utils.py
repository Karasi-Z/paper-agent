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

This module provides file utility helpers for Paper Agent.

Description of Class and Function
--------------------------------
(1) ensure_directory
    - Ensure a directory exists

(2) read_text_file
    - Read local file as text

(3) write_text_file
    - Write local file as text
"""


from pathlib import Path


def ensure_directory(path: str | Path) -> Path:
    """
    Function Function:

        Ensure the target directory exists.
    """

    target_path = Path(path)
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


def read_text_file(path: str | Path) -> str:
    """
    Function Function:

        Read a local file as UTF-8 text with tolerant decoding.
    """

    return Path(path).read_text(encoding="utf-8", errors="ignore")


def write_text_file(path: str | Path, text: str) -> Path:
    """
    Function Function:

        Write UTF-8 text to local file.
    """

    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")
    return file_path


###################################################################################################
###################################################################################################
### End of file
