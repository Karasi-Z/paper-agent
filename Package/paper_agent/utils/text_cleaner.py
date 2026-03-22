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

This module provides text normalization, tokenization, sentence splitting,
keyword extraction, and chunk slicing utilities for Paper Agent.

Description of Class and Function
--------------------------------
(1) normalize_whitespace
    - Normalize noisy text content

(2) tokenize
    - Tokenize text for scoring and keyword extraction

(3) split_sentences
    - Split text into natural sentences

(4) chunk_words
    - Slice text into overlapping chunks

(5) extract_keywords
    - Extract simple high-frequency keywords
"""


import re
from collections import Counter
from typing import Iterable


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "using",
    "paper",
    "study",
    "approach",
    "method",
    "methods",
    "results",
    "have",
    "has",
    "had",
    "into",
    "their",
    "our",
    "what",
    "when",
    "where",
    "which",
    "论文",
    "方法",
    "结果",
    "研究",
    "本文",
}

ZH_EN_GLOSSARY = {
    "摘要": ["abstract"],
    "引言": ["introduction"],
    "背景": ["background"],
    "相关工作": ["related work"],
    "方法": ["method", "approach"],
    "框架": ["framework"],
    "模型": ["model"],
    "双层": ["bilevel"],
    "双层规划": ["bilevel programming"],
    "混合整数规划": ["mixed integer programming", "mip"],
    "精确": ["exact"],
    "算法": ["algorithm"],
    "求解": ["solve", "solution"],
    "求解框架": ["solution framework"],
    "结论": ["conclusion"],
    "实验": ["experiment"],
    "结果": ["result"],
    "敏感性分析": ["sensitivity analysis"],
    "航空公司": ["airline"],
    "服务提供商": ["service provider"],
    "维护服务提供商": ["maintenance service provider", "msp"],
    "维修服务提供商": ["maintenance service provider", "msp"],
    "外包": ["outsourcing"],
    "合作": ["cooperation"],
}

EN_ZH_GLOSSARY = {
    "abstract": ["摘要"],
    "introduction": ["引言"],
    "background": ["背景"],
    "related work": ["相关工作"],
    "method": ["方法"],
    "approach": ["方法"],
    "framework": ["框架"],
    "model": ["模型"],
    "bilevel": ["双层"],
    "mixed integer programming": ["混合整数规划"],
    "mip": ["混合整数规划", "MIP"],
    "exact": ["精确"],
    "algorithm": ["算法"],
    "solution framework": ["求解框架"],
    "conclusion": ["结论"],
    "experiment": ["实验"],
    "result": ["结果"],
    "sensitivity analysis": ["敏感性分析"],
    "airline": ["航空公司"],
    "service provider": ["服务提供商"],
    "maintenance service provider": ["维护服务提供商", "MSP"],
    "msp": ["维护服务提供商", "MSP"],
    "outsourcing": ["外包"],
    "cooperation": ["合作"],
}


def normalize_whitespace(text: str) -> str:
    """
    Function Function:

        Normalize whitespace and control characters in text.
    """

    normalized_text = text.replace("\x00", " ")
    normalized_text = re.sub(r"[ \t]+", " ", normalized_text)
    normalized_text = re.sub(r" *\n *", "\n", normalized_text)
    normalized_text = re.sub(r"\n{3,}", "\n\n", normalized_text)
    return normalized_text.strip()


def tokenize(text: str) -> list[str]:
    """
    Function Function:

        Tokenize text into alphanumeric lowercase tokens.
    """

    token_list = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    for segment in re.findall(r"[\u4e00-\u9fff]+", text):
        token_list.extend(list(segment))
        if len(segment) > 1:
            token_list.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return token_list


def detect_language(text: str) -> str:
    """
    Function Function:

        Detect whether text is primarily Chinese or English.
    """

    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    english_count = len(re.findall(r"[A-Za-z]", text))
    return "zh" if chinese_count > english_count else "en"


def expand_query_for_retrieval(text: str) -> str:
    """
    Function Function:

        Expand query with lightweight bilingual terminology for cross-language retrieval.
    """

    normalized_text = text.strip()
    lowered_text = normalized_text.lower()
    expansion_list: list[str] = []
    if detect_language(normalized_text) == "zh":
        for phrase, translations in ZH_EN_GLOSSARY.items():
            if phrase in normalized_text:
                expansion_list.extend(translations)
    else:
        for phrase, translations in EN_ZH_GLOSSARY.items():
            if phrase in lowered_text:
                expansion_list.extend(translations)

    if not expansion_list:
        return normalized_text

    unique_expansion_list: list[str] = []
    seen_text_set = {normalized_text}
    for item in expansion_list:
        cleaned_item = item.strip()
        if cleaned_item and cleaned_item not in seen_text_set:
            seen_text_set.add(cleaned_item)
            unique_expansion_list.append(cleaned_item)
    if not unique_expansion_list:
        return normalized_text
    return f"{normalized_text}\n\nQuery expansion: {' '.join(unique_expansion_list)}"


def split_sentences(text: str) -> list[str]:
    """
    Function Function:

        Split text into approximate sentence units.
    """

    cleaned_text = normalize_whitespace(text)
    sentence_list = re.split(r"(?<=[.!?。！？])\s+", cleaned_text)
    return [item.strip() for item in sentence_list if item.strip()]


def chunk_words(text: str, size: int, overlap: int) -> list[str]:
    """
    Function Function:

        Slice text into overlapping word chunks.
    """

    word_list = text.split()
    if not word_list:
        return []

    chunk_list: list[str] = []
    step = max(1, size - overlap)
    for start in range(0, len(word_list), step):
        chunk_text = " ".join(word_list[start : start + size]).strip()
        if chunk_text:
            chunk_list.append(chunk_text)
        if start + size >= len(word_list):
            break
    return chunk_list


def extract_keywords(texts: Iterable[str], limit: int = 6) -> list[str]:
    """
    Function Function:

        Extract simple keywords from a group of texts.
    """

    counter: Counter[str] = Counter()
    for text in texts:
        for token in tokenize(text):
            if len(token) < 3 or token in STOPWORDS:
                continue
            counter[token] += 1
    return [token for token, _ in counter.most_common(limit)]


def sentence_overlap_score(sentence: str, query_tokens: set[str]) -> float:
    """
    Function Function:

        Calculate token-overlap score between sentence and query.
    """

    sentence_tokens = set(tokenize(sentence))
    if not sentence_tokens or not query_tokens:
        return 0.0
    return len(sentence_tokens & query_tokens) / max(1, len(sentence_tokens))


###################################################################################################
###################################################################################################
### End of file
