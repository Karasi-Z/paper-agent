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

This module implements the cluster agent for Paper Agent.
"""


from collections import defaultdict

import numpy as np

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
except Exception:  # pragma: no cover
    KMeans = None
    silhouette_score = None

from paper_agent.models.entities import Cluster, Paper
from paper_agent.utils.text_cleaner import extract_keywords


class ClusterAgent:
    """
    ClusterAgent
    ------------
    Topic clustering agent for literature collections.
    """

    def __init__(self, max_clusters: int) -> None:
        """
        Function Function:

            Initialize cluster agent.
        """

        self.max_clusters = max_clusters

    def cluster(self, project_id: str, paper_list: list[Paper], ordered_paper_ids: list[str], paper_matrix: np.ndarray) -> list[Cluster]:
        """
        Function Function:

            Cluster paper vectors into topical groups.
        """

        if len(paper_list) == 0:
            return []

        if len(paper_list) < 3 or paper_matrix.shape[0] < 3 or KMeans is None:
            keyword_list = extract_keywords([item.title + " " + item.abstract for item in paper_list], limit=3)
            return [
                Cluster(
                    project_id=project_id,
                    label=" / ".join(keyword_list) if keyword_list else "general",
                    paper_ids=[item.paper_id for item in paper_list],
                    keywords=keyword_list,
                    summary=f"A single topic group containing {len(paper_list)} papers.",
                    representative_papers=[paper_list[0].paper_id],
                )
            ]

        best_k = self._choose_cluster_count(paper_matrix)
        estimator = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        label_array = estimator.fit_predict(paper_matrix)
        paper_map = {item.paper_id: item for item in paper_list}
        grouped_paper_id_map: dict[int, list[str]] = defaultdict(list)
        for paper_id, label in zip(ordered_paper_ids, label_array, strict=False):
            grouped_paper_id_map[int(label)].append(paper_id)

        cluster_list: list[Cluster] = []
        for label, group_paper_id_list in grouped_paper_id_map.items():
            group_paper_list = [paper_map[paper_id] for paper_id in group_paper_id_list if paper_id in paper_map]
            keyword_list = extract_keywords([item.title + " " + item.abstract for item in group_paper_list], limit=5)
            representative_paper_list = self._pick_representatives(
                group_paper_id_list,
                ordered_paper_ids,
                paper_matrix,
                estimator.cluster_centers_[label],
            )
            cluster_list.append(
                Cluster(
                    project_id=project_id,
                    label=" / ".join(keyword_list[:3]) if keyword_list else f"cluster-{label + 1}",
                    paper_ids=group_paper_id_list,
                    keywords=keyword_list,
                    summary=f"Cluster {label + 1} focuses on {', '.join(keyword_list[:4]) or 'mixed topics'}.",
                    representative_papers=representative_paper_list,
                )
            )

        cluster_list.sort(key=lambda item: len(item.paper_ids), reverse=True)
        return cluster_list

    def _choose_cluster_count(self, paper_matrix: np.ndarray) -> int:
        """
        Function Function:

            Choose cluster count by silhouette score.
        """

        max_candidate = min(self.max_clusters, paper_matrix.shape[0] - 1)
        if max_candidate < 2 or silhouette_score is None or KMeans is None:
            return 1

        best_score = -1.0
        best_k = 2
        for k in range(2, max_candidate + 1):
            estimator = KMeans(n_clusters=k, random_state=42, n_init=10)
            label_array = estimator.fit_predict(paper_matrix)
            if len(set(label_array)) < 2:
                continue
            score = float(silhouette_score(paper_matrix, label_array))
            if score > best_score:
                best_score = score
                best_k = k
        return best_k

    def _pick_representatives(
        self,
        group_paper_id_list: list[str],
        ordered_paper_ids: list[str],
        paper_matrix: np.ndarray,
        centroid: np.ndarray,
    ) -> list[str]:
        """
        Function Function:

            Pick representative papers closest to centroid.
        """

        distance_list: list[tuple[float, str]] = []
        for paper_id in group_paper_id_list:
            matrix_index = ordered_paper_ids.index(paper_id)
            distance_list.append((float(np.linalg.norm(paper_matrix[matrix_index] - centroid)), paper_id))
        distance_list.sort(key=lambda item: item[0])
        return [paper_id for _, paper_id in distance_list[: min(3, len(distance_list))]]


###################################################################################################
###################################################################################################
### End of file
