"""Tests for GitHub Discussions Fetcher."""

from api.services.github_fetcher import GitHubDiscussionsFetcher


class TestDiscussionToMessages:
    def setup_method(self):
        self.fetcher = GitHubDiscussionsFetcher("fake_token")

    def test_basic_discussion(self):
        discussion = {
            "id": "D_001",
            "title": "How to use middleware?",
            "body": "I want to add auth middleware.",
            "url": "https://github.com/vercel/next.js/discussions/1",
            "author": "alice",
            "created_at": "2026-02-20T10:00:00Z",
            "category": {"id": "cat1", "name": "Q&A"},
            "answer": None,
            "comments": [
                {"id": "DC_002", "body": "Create middleware.ts in root.", "author": "bob", "created_at": "2026-02-20T11:00:00Z"},
            ],
        }
        messages = self.fetcher.discussion_to_messages(discussion)
        assert len(messages) == 2
        assert messages[0]["content"].startswith("# How to use middleware?")
        assert messages[0]["reply_to"] is None
        assert messages[1]["reply_to"] == "D_001"

    def test_discussion_with_answer(self):
        discussion = {
            "id": "D_003",
            "title": "Config question",
            "body": "How do I configure X?",
            "url": "https://github.com/org/repo/discussions/3",
            "author": "user1",
            "created_at": "2026-02-20T10:00:00Z",
            "category": {"id": "cat1", "name": "Q&A"},
            "answer": {"id": "DC_answer", "body": "Set X=true in config.", "author": {"login": "expert"}, "createdAt": "2026-02-20T12:00:00Z"},
            "comments": [
                {"id": "DC_004", "body": "I also want to know.", "author": "user2", "created_at": "2026-02-20T11:00:00Z"},
            ],
        }
        messages = self.fetcher.discussion_to_messages(discussion)
        assert len(messages) == 3  # OP + comment + answer
        answer_msgs = [m for m in messages if "[ACCEPTED ANSWER]" in m["content"]]
        assert len(answer_msgs) == 1

    def test_no_comments(self):
        discussion = {
            "id": "D_005",
            "title": "Feature request",
            "body": "Please add X.",
            "url": "https://github.com/org/repo/discussions/5",
            "author": "user1",
            "created_at": "2026-02-20T10:00:00Z",
            "category": {"id": "cat1", "name": "Ideas"},
            "answer": None,
            "comments": [],
        }
        messages = self.fetcher.discussion_to_messages(discussion)
        assert len(messages) == 1  # Only OP

    def test_author_hashing(self):
        h1 = self.fetcher.hash_username("alice")
        h2 = self.fetcher.hash_username("alice")
        h3 = self.fetcher.hash_username("bob")
        assert h1 == h2  # Deterministic
        assert h1 != h3  # Unique
        assert len(h1) == 64  # SHA-256

    def test_op_content_includes_title(self):
        discussion = {
            "id": "D_006",
            "title": "Important Question",
            "body": "Details here.",
            "url": "https://github.com/org/repo/discussions/6",
            "author": "alice",
            "created_at": "2026-02-20T10:00:00Z",
            "category": {},
            "answer": None,
            "comments": [],
        }
        messages = self.fetcher.discussion_to_messages(discussion)
        assert "# Important Question" in messages[0]["content"]
        assert "Details here." in messages[0]["content"]
