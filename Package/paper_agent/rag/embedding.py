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

This module implements embedding providers for Paper Agent.

The module supports:

- local deterministic hash embedding fallback
- local Ollama embedding model integration
- optional sentence-transformer embedding integration

Description of Class and Function
--------------------------------
(1) BaseEmbeddingProvider
    - Embedding provider interface

(2) HashEmbeddingProvider
    - Lightweight deterministic fallback embedding provider

(3) OllamaEmbeddingProvider
    - Ollama embedding provider with automatic fallback

(4) SentenceTransformerEmbeddingProvider
    - Sentence-transformer embedding provider with automatic fallback

(5) build_embedding_provider
    - Embedding provider factory
"""


import hashlib
import math
from abc import ABC, abstractmethod
from typing import Iterable

import numpy as np

from paper_agent.utils.text_cleaner import tokenize

try:
    import ollama
except Exception:  # pragma: no cover
    ollama = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None


class BaseEmbeddingProvider(ABC):
    """
    BaseEmbeddingProvider
    ---------------------
    Abstract embedding provider interface.
    """

    def __init__(self, model_name: str, dim: int) -> None:
        """
        Function Function:

            Initialize embedding provider.
        """

        self.model_name = model_name
        self.dim = dim

    @abstractmethod
    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        """
        Function Function:

            Embed a group of texts.
        """

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """
        Function Function:

            Embed one query string.
        """


class HashEmbeddingProvider(BaseEmbeddingProvider):
    """
    HashEmbeddingProvider
    ---------------------
    Deterministic hash-based embedding fallback.
    """

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        """
        Function Function:

            Embed a group of texts by deterministic hashing.
        """

        return [self._embed_single(text).tolist() for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """
        Function Function:

            Embed one query by deterministic hashing.
        """

        return self._embed_single(text).tolist()

    def _embed_single(self, text: str) -> np.ndarray:
        """
        Function Function:

            Embed one string by signed token hashing.
        """

        vector = np.zeros(self.dim, dtype=float)
        for token in tokenize(text):
            bucket = self._stable_hash(token) % self.dim
            sign = 1.0 if self._stable_hash(f"{token}:sign") % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(float(np.dot(vector, vector)))
        if norm > 0:
            vector /= norm
        return vector

    def _stable_hash(self, text: str) -> int:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big", signed=False)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """
    OllamaEmbeddingProvider
    -----------------------
    Embedding provider backed by local Ollama.
    """

    def __init__(self, model_name: str, host: str, dim: int = 1024) -> None:
        """
        Function Function:

            Initialize Ollama embedding provider.
        """

        super().__init__(model_name=model_name, dim=dim)
        self.host = host
        self.hash_fallback = HashEmbeddingProvider(
            model_name=f"{model_name}-hash-fallback",
            dim=dim,
        )

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        """
        Function Function:

            Embed multiple texts using Ollama.
        """

        text_list = list(texts)
        if not text_list:
            return []

        try:
            if ollama is None:
                raise RuntimeError("ollama package is not available")
            client = ollama.Client(host=self.host)
            response = client.embed(model=self.model_name, input=text_list)
            embedding_list = [list(item) for item in response.get("embeddings", [])]
            if embedding_list:
                return embedding_list
        except Exception:
            pass
        return self.hash_fallback.embed_documents(text_list)

    def embed_query(self, text: str) -> list[float]:
        """
        Function Function:

            Embed query using Ollama.
        """

        result_list = self.embed_documents([text])
        return result_list[0] if result_list else [0.0] * self.dim


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    """
    SentenceTransformerEmbeddingProvider
    ------------------------------------
    Sentence-transformer based embedding provider.
    """

    def __init__(self, model_name: str, dim: int) -> None:
        """
        Function Function:

            Initialize sentence-transformer embedding provider.
        """

        super().__init__(model_name=model_name, dim=dim)
        self.hash_fallback = HashEmbeddingProvider(
            model_name=f"{model_name}-hash-fallback",
            dim=dim,
        )
        self._model = None

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        """
        Function Function:

            Embed multiple texts using sentence-transformers.
        """

        text_list = list(texts)
        if not text_list:
            return []

        try:
            if SentenceTransformer is None:
                raise RuntimeError("sentence-transformers package is not available")
            if self._model is None:
                self._model = SentenceTransformer(self.model_name)
            embedding_array = self._model.encode(text_list, normalize_embeddings=True)
            return np.asarray(embedding_array, dtype=float).tolist()
        except Exception:
            return self.hash_fallback.embed_documents(text_list)

    def embed_query(self, text: str) -> list[float]:
        """
        Function Function:

            Embed query using sentence-transformers.
        """

        result_list = self.embed_documents([text])
        return result_list[0] if result_list else [0.0] * self.dim


def build_embedding_provider(
    provider_name: str,
    model_name: str,
    host: str,
    dim: int,
) -> BaseEmbeddingProvider:
    """
    Function Function:

        Build embedding provider from configuration.
    """

    if provider_name == "ollama":
        return OllamaEmbeddingProvider(model_name=model_name, host=host, dim=dim)
    if provider_name in {"bge-m3", "sentence_transformer", "sentence-transformers"}:
        return SentenceTransformerEmbeddingProvider(model_name=model_name, dim=dim)
    return HashEmbeddingProvider(model_name=model_name, dim=dim)


###################################################################################################
###################################################################################################
### End of file
