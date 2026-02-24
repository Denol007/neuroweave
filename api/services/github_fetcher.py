"""GitHub Discussions Fetcher — fetches discussions via GraphQL API.

Converts GitHub Discussions + comments into the message format
expected by the NeuroWeave extraction pipeline.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

import httpx
import structlog

logger = structlog.get_logger()

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

DISCUSSIONS_QUERY = """
query($owner: String!, $repo: String!, $first: Int!, $after: String, $categoryId: ID) {
  repository(owner: $owner, name: $repo) {
    discussions(first: $first, after: $after, categoryId: $categoryId, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo { hasNextPage, endCursor }
      nodes {
        id
        number
        title
        body
        url
        createdAt
        updatedAt
        author { login }
        answer {
          id
          body
          author { login }
          createdAt
        }
        category { id, name }
        comments(first: 50) {
          nodes {
            id
            body
            author { login }
            createdAt
          }
        }
      }
    }
  }
}
"""

CATEGORIES_QUERY = """
query($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    discussionCategories(first: 25) {
      nodes { id, name, emoji, description }
    }
  }
}
"""


class GitHubDiscussionsFetcher:
    """Fetches GitHub Discussions via GraphQL API."""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _graphql(self, query: str, variables: dict) -> dict:
        """Execute a GraphQL query against GitHub API."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GITHUB_GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()

            if "errors" in data:
                logger.error("github_graphql_error", errors=data["errors"])
                raise RuntimeError(f"GraphQL errors: {data['errors']}")

            return data["data"]

    async def fetch_categories(self, owner: str, repo: str) -> list[dict]:
        """Fetch discussion categories for a repository."""
        data = await self._graphql(CATEGORIES_QUERY, {"owner": owner, "repo": repo})
        return data["repository"]["discussionCategories"]["nodes"]

    async def fetch_discussions(
        self,
        owner: str,
        repo: str,
        category_id: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Fetch discussions from a repository with pagination.

        Args:
            owner: GitHub org/user.
            repo: Repository name.
            category_id: Optional category ID filter.
            limit: Max discussions to fetch (paginates automatically).

        Returns:
            List of discussion dicts with title, body, comments, etc.
        """
        discussions = []
        cursor = None
        remaining = limit

        while remaining > 0:
            page_size = min(remaining, 50)
            variables: dict = {"owner": owner, "repo": repo, "first": page_size}
            if category_id:
                variables["categoryId"] = category_id
            if cursor:
                variables["after"] = cursor

            data = await self._graphql(DISCUSSIONS_QUERY, variables)
            disc_data = data["repository"]["discussions"]
            nodes = disc_data["nodes"]
            page_info = disc_data["pageInfo"]

            if not nodes:
                break

            for node in nodes:
                if not node.get("body"):
                    continue

                discussions.append({
                    "id": node["id"],
                    "number": node["number"],
                    "title": node["title"],
                    "body": node["body"],
                    "url": node["url"],
                    "author": (node.get("author") or {}).get("login", "ghost"),
                    "created_at": node["createdAt"],
                    "updated_at": node["updatedAt"],
                    "category": node.get("category", {}),
                    "answer": node.get("answer"),
                    "comments": [
                        {
                            "id": c["id"],
                            "body": c["body"],
                            "author": (c.get("author") or {}).get("login", "ghost"),
                            "created_at": c["createdAt"],
                        }
                        for c in node.get("comments", {}).get("nodes", [])
                        if c.get("body")
                    ],
                })

            remaining -= len(nodes)

            # Pagination: continue if more pages and haven't hit limit
            if page_info.get("hasNextPage") and remaining > 0:
                cursor = page_info["endCursor"]
                logger.info("github_paginating", fetched=len(discussions), remaining=remaining)
            else:
                break

        logger.info("github_discussions_fetched", owner=owner, repo=repo, count=len(discussions))
        return discussions

    @staticmethod
    def hash_username(username: str) -> str:
        """SHA-256 hash a GitHub username for consistency with Discord flow."""
        return hashlib.sha256(username.encode()).hexdigest()

    def discussion_to_messages(self, discussion: dict) -> list[dict]:
        """Convert a GitHub Discussion + comments into pipeline message format.

        Each discussion becomes a pre-threaded batch of messages:
        - First message: title + body (from OP)
        - Subsequent messages: each comment
        - If discussion has an accepted answer, it's marked

        Returns:
            List of message dicts matching the pipeline input format:
            {id, author_hash, content, timestamp, reply_to, mentions}
        """
        messages = []

        # First message: discussion title + body
        op_content = f"# {discussion['title']}\n\n{discussion['body']}"
        messages.append({
            "id": discussion["id"],
            "author_hash": self.hash_username(discussion["author"]),
            "content": op_content,
            "timestamp": discussion["created_at"],
            "reply_to": None,
            "mentions": [],
        })

        # Comments
        for comment in discussion.get("comments", []):
            messages.append({
                "id": comment["id"],
                "author_hash": self.hash_username(comment["author"]),
                "content": comment["body"],
                "timestamp": comment["created_at"],
                "reply_to": discussion["id"],
                "mentions": [],
            })

        # If there's an accepted answer and it's not already in comments
        answer = discussion.get("answer")
        if answer and answer["id"] not in {m["id"] for m in messages}:
            messages.append({
                "id": answer["id"],
                "author_hash": self.hash_username((answer.get("author") or {}).get("login", "ghost")),
                "content": f"[ACCEPTED ANSWER]\n\n{answer['body']}",
                "timestamp": answer["createdAt"],
                "reply_to": discussion["id"],
                "mentions": [],
            })

        return messages
