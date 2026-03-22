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

This module implements the RAG vector service for Paper Agent.

Description of Class and Function
--------------------------------
(1) RagVectorService
    - Embedding and ChromaDB orchestration service
"""


from paper_agent.dao.chunk_dao import ChunkDao
from paper_agent.models.entities import Paper, PaperChunk
from paper_agent.rag.embedding import BaseEmbeddingProvider
from paper_agent.store.chroma_store import ChromaVectorStore
from paper_agent.utils.text_cleaner import expand_query_for_retrieval, tokenize


class RagVectorService:
    """
    RagVectorService
    ----------------
    Embedding plus ChromaDB orchestration service.
    """

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        chroma_store: ChromaVectorStore,
        chunk_dao: ChunkDao | None = None,
    ) -> None:
        """
        Function Function:

            Initialize RAG vector service.
        """

        self.embedding_provider = embedding_provider
        self.chroma_store = chroma_store
        self.chunk_dao = chunk_dao

    def index_chunks(self, project_id: str, paper: Paper, chunk_list: list[PaperChunk]) -> None:
        """
        Function Function:

            Index chunk vectors into ChromaDB.
        """

        if not chunk_list:
            return
        self.chroma_store.delete_paper_chunks(paper.paper_id)
        embedding_list = self.embedding_provider.embed_documents(item.content for item in chunk_list)
        id_list = [item.chunk_id for item in chunk_list]
        document_list = [item.content for item in chunk_list]
        metadata_list = [
            {
                "project_id": project_id,
                "paper_id": paper.paper_id,
                "paper_title": paper.title,
                "chunk_index": item.chunk_index,
                "section_title": item.section_title,
                "page_start": item.page_start,
                "page_end": item.page_end,
            }
            for item in chunk_list
        ]
        self.chroma_store.upsert_chunks(
            ids=id_list,
            embeddings=embedding_list,
            documents=document_list,
            metadatas=metadata_list,
        )

    def index_paper(self, project_id: str, paper: Paper) -> None:
        """
        Function Function:

            Index paper-level vector into ChromaDB.
        """

        combined_text = "\n\n".join(part for part in [paper.title, paper.abstract, paper.content_text] if part).strip()
        embedding_list = self.embedding_provider.embed_documents([combined_text])
        self.chroma_store.delete_paper_vector(paper.paper_id)
        self.chroma_store.upsert_papers(
            ids=[paper.paper_id],
            embeddings=embedding_list,
            documents=[combined_text],
            metadatas=[
                {
                    "project_id": project_id,
                    "paper_id": paper.paper_id,
                    "paper_title": paper.title,
                }
            ],
        )

    def search_chunks(self, project_id: str, query: str, top_k: int) -> list[dict]:
        """
        Function Function:

            Search top-k chunk evidence from ChromaDB.
        """

        ranked_item_map: dict[str, dict] = {}

        expanded_query = expand_query_for_retrieval(query)
        query_embedding = self.embedding_provider.embed_query(expanded_query)
        query_result = self.chroma_store.query_chunks(
            query_embedding=query_embedding,
            top_k=max(top_k, 10),
            where={"project_id": project_id},
        )

        document_list = (query_result.get("documents") or [[]])[0]
        metadata_list = (query_result.get("metadatas") or [[]])[0]
        distance_list = (query_result.get("distances") or [[]])[0]
        id_list = (query_result.get("ids") or [[]])[0]

        query_token_set = set(tokenize(expanded_query))
        for chunk_id, document, metadata, distance in zip(id_list, document_list, metadata_list, distance_list, strict=False):
            overlap_score = len(query_token_set & set(tokenize(document))) / max(1, len(query_token_set) or 1)
            semantic_score = float((1.0 / (1.0 + float(distance))) + 0.15 * overlap_score)
            ranked_item_map[chunk_id] = {
                "chunk_id": chunk_id,
                "document": document,
                "metadata": metadata,
                "distance": float(distance),
                "semantic_score": semantic_score,
                "lexical_score": 0.0,
                "retrieval_channels": ["vector"],
            }

        if self.chunk_dao is not None:
            lexical_item_list = self.chunk_dao.search_project_chunks(
                project_id=project_id,
                query=expanded_query,
                limit=max(top_k, 10),
            )
            for item in lexical_item_list:
                chunk_id = item["chunk_id"]
                lexical_score = float(item.get("score", 0.0))
                if chunk_id in ranked_item_map:
                    ranked_item_map[chunk_id]["lexical_score"] = max(ranked_item_map[chunk_id]["lexical_score"], lexical_score)
                    if "fts" not in ranked_item_map[chunk_id]["retrieval_channels"]:
                        ranked_item_map[chunk_id]["retrieval_channels"].append("fts")
                    continue
                ranked_item_map[chunk_id] = {
                    "chunk_id": chunk_id,
                    "document": item.get("document", ""),
                    "metadata": item.get("metadata", {}),
                    "distance": None,
                    "semantic_score": 0.0,
                    "lexical_score": lexical_score,
                    "retrieval_channels": ["fts"],
                }

        ranked_item_list: list[dict] = []
        for item in ranked_item_map.values():
            hybrid_score = 0.65 * float(item.get("semantic_score", 0.0)) + 0.35 * float(item.get("lexical_score", 0.0))
            ranked_item_list.append(
                {
                    "chunk_id": item["chunk_id"],
                    "document": item["document"],
                    "metadata": item["metadata"],
                    "distance": item.get("distance"),
                    "score": hybrid_score,
                    "semantic_score": item.get("semantic_score", 0.0),
                    "lexical_score": item.get("lexical_score", 0.0),
                    "retrieval_channels": item.get("retrieval_channels", []),
                }
            )
        ranked_item_list.sort(key=lambda item: item["score"], reverse=True)
        return ranked_item_list[: max(top_k, 10)]

    def get_paper_matrix(self, paper_id_list: list[str]):
        """
        Function Function:

            Fetch paper embedding matrix for clustering.
        """

        return self.chroma_store.get_paper_matrix(paper_id_list)


###################################################################################################
###################################################################################################
### End of file
