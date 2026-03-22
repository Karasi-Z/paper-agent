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

This module implements the indexing agent for Paper Agent.
"""


from paper_agent.dao.chunk_dao import ChunkDao
from paper_agent.models.entities import Paper, PaperChunk
from paper_agent.rag.vector_store import RagVectorService


class IndexAgent:
    """
    IndexAgent
    ----------
    Chunk and vector indexing agent.
    """

    def __init__(self, chunk_dao: ChunkDao, vector_service: RagVectorService) -> None:
        """
        Function Function:

            Initialize index agent.
        """

        self.chunk_dao = chunk_dao
        self.vector_service = vector_service

    def index_paper(self, project_id: str, paper: Paper, chunk_list: list[PaperChunk]) -> list[PaperChunk]:
        """
        Function Function:

            Persist chunks and index vectors for one paper.
        """

        self.chunk_dao.replace_chunks(paper.paper_id, chunk_list)
        self.vector_service.index_chunks(project_id=project_id, paper=paper, chunk_list=chunk_list)
        self.vector_service.index_paper(project_id=project_id, paper=paper)
        return chunk_list


###################################################################################################
###################################################################################################
### End of file
