"""Disentanglement Engine — clusters raw Discord messages into logical threads.

Discord channels are chaotic: multiple conversations happen simultaneously.
This module uses Sentence-BERT embeddings + cosine similarity + temporal
clustering to group related messages into coherent threads.

Algorithm:
1. Generate 384-dim embeddings for all messages (all-MiniLM-L6-v2)
2. Compute pairwise cosine similarity matrix
3. Build adjacency graph using:
   - Semantic similarity > threshold (0.75)
   - Temporal proximity (within 4-hour window)
   - Explicit links: reply_to references, @mentions
4. Find connected components via BFS → each component = one thread
5. Sort messages within each thread by timestamp
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from api.services.embeddings import encode_batch


@dataclass
class RawMessage:
    """A raw Discord message before thread clustering."""

    id: str
    author_hash: str
    content: str
    timestamp: datetime
    has_code: bool = False
    reply_to: str | None = None
    mentions: list[str] = field(default_factory=list)


class DisentanglementEngine:
    """Clusters raw Discord messages into logical conversation threads."""

    SIMILARITY_THRESHOLD = 0.45
    TEMPORAL_WINDOW = timedelta(hours=4)
    SAME_AUTHOR_BOOST = 0.25
    ERROR_CODE_BOOST = 0.20
    SAME_AUTHOR_WINDOW = timedelta(minutes=10)

    def cluster(self, messages: list[RawMessage]) -> list[list[RawMessage]]:
        """Main entry point: takes raw messages, returns grouped threads.

        Args:
            messages: List of raw Discord messages, chronologically ordered.

        Returns:
            List of threads, each thread is a list of RawMessage sorted by timestamp.
            Single isolated messages are returned as single-element threads.
        """
        if not messages:
            return []

        if len(messages) == 1:
            return [messages]

        # Step 1: Generate embeddings for all messages
        texts = [m.content for m in messages]
        embeddings = encode_batch(texts)

        # Step 2: Compute pairwise cosine similarity matrix
        sim_matrix = cosine_similarity(embeddings)

        # Step 3: Build adjacency graph
        n = len(messages)
        adjacency = np.zeros((n, n), dtype=bool)

        for i in range(n):
            for j in range(i + 1, n):
                if self._should_link(messages, sim_matrix, i, j):
                    adjacency[i][j] = True
                    adjacency[j][i] = True

        # Step 4: Find connected components via BFS
        visited: set[int] = set()
        threads: list[list[RawMessage]] = []

        for start in range(n):
            if start in visited:
                continue

            queue = [start]
            component: list[int] = []

            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)

                for neighbor in range(n):
                    if adjacency[node][neighbor] and neighbor not in visited:
                        queue.append(neighbor)

            # Sort by timestamp within thread
            component.sort(key=lambda idx: messages[idx].timestamp)
            threads.append([messages[idx] for idx in component])

        return threads

    def _should_link(
        self,
        messages: list[RawMessage],
        sim_matrix: np.ndarray,
        i: int,
        j: int,
    ) -> bool:
        """Determine if two messages should be in the same thread."""
        msg_i = messages[i]
        msg_j = messages[j]

        # Temporal gate: messages must be within the time window
        time_delta = abs(msg_i.timestamp - msg_j.timestamp)
        if time_delta > self.TEMPORAL_WINDOW:
            return False

        # Explicit link: reply_to
        if msg_j.reply_to and msg_j.reply_to == msg_i.id:
            return True
        if msg_i.reply_to and msg_i.reply_to == msg_j.id:
            return True

        # Explicit link: @mention of the other author
        if msg_i.author_hash in msg_j.mentions:
            return True
        if msg_j.author_hash in msg_i.mentions:
            return True

        # Compute effective similarity with boosts
        similarity = float(sim_matrix[i][j])

        # Boost: same author within 60 seconds (likely continuation)
        if (
            msg_i.author_hash == msg_j.author_hash
            and time_delta <= self.SAME_AUTHOR_WINDOW
        ):
            similarity += self.SAME_AUTHOR_BOOST

        # Boost: both messages contain code blocks (likely same tech discussion)
        if msg_i.has_code and msg_j.has_code:
            similarity += self.ERROR_CODE_BOOST

        return similarity >= self.SIMILARITY_THRESHOLD
