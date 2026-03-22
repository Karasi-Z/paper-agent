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

This module implements the ChromaDB vector store for Paper Agent.

The store is used for:

- chunk vector indexing and query
- paper vector indexing and export for clustering
- persistent local vector storage

Description of Class and Function
--------------------------------
(1) ChromaVectorStore
    - ChromaDB persistent vector store
"""


from pathlib import Path

import chromadb
import numpy as np


class ChromaVectorStore:
    """
    ChromaVectorStore
    -----------------
    Persistent ChromaDB vector store wrapper.
    """

    def __init__(self, persist_dir: str | Path) -> None:
        """
        Function Function:

            Initialize ChromaDB persistent client and collections.
        """

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.chunk_collection = self.client.get_or_create_collection(name="paper_agent_chunks")
        self.paper_collection = self.client.get_or_create_collection(name="paper_agent_papers")

    def upsert_chunks(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        Function Function:

            Upsert chunk vectors into ChromaDB.
        """

        if not ids:
            return
        self.chunk_collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def upsert_papers(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        Function Function:

            Upsert paper vectors into ChromaDB.
        """

        if not ids:
            return
        self.paper_collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    def query_chunks(self, query_embedding: list[float], top_k: int, where: dict | None = None) -> dict:
        """
        Function Function:

            Query chunk vectors from ChromaDB.
        """

        return self.chunk_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

    def get_paper_matrix(self, paper_ids: list[str]) -> tuple[list[str], np.ndarray]:
        """
        Function Function:

            Fetch paper embeddings matrix for clustering.
        """

        if not paper_ids:
            return [], np.zeros((0, 0), dtype=float)

        result = self.paper_collection.get(ids=paper_ids, include=["embeddings", "metadatas"])
        id_list = result.get("ids", [])
        embedding_array = result.get("embeddings")
        if embedding_array is None:
            return [], np.zeros((0, 0), dtype=float)
        paper_matrix = np.array(embedding_array, dtype=float)
        if paper_matrix.size == 0:
            return [], np.zeros((0, 0), dtype=float)
        return list(id_list), paper_matrix

    def delete_paper_chunks(self, paper_id: str) -> None:
        """
        Function Function:

            Delete all chunk vectors for a paper.
        """

        self.chunk_collection.delete(where={"paper_id": paper_id})

    def delete_paper_vector(self, paper_id: str) -> None:
        """
        Function Function:

            Delete paper-level vector for a paper.
        """

        self.paper_collection.delete(ids=[paper_id])


###################################################################################################
###################################################################################################
### End of file
