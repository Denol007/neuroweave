"""Shared test fixtures for all test modules."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from api.services.extraction.disentanglement import RawMessage


@pytest.fixture
def sample_messages() -> list[RawMessage]:
    """6 Discord messages: 2 greetings + 4 tech discussion."""
    now = datetime(2026, 2, 22, 14, 0, 0)
    return [
        RawMessage(id="1", author_hash="aaa", content="Hey everyone! Happy Monday", timestamp=now),
        RawMessage(id="2", author_hash="bbb", content="gm gm", timestamp=now + timedelta(seconds=30)),
        RawMessage(
            id="3", author_hash="ccc",
            content="Anyone seen this error with Next.js 14?\n```\nError: ENOMEM not enough memory\n```",
            timestamp=now + timedelta(minutes=2), has_code=True,
        ),
        RawMessage(
            id="4", author_hash="ddd",
            content="yeah that's an OOM during build, try reducing worker threads",
            timestamp=now + timedelta(minutes=4), mentions=["ccc"],
        ),
        RawMessage(
            id="5", author_hash="ddd",
            content="Try adding this to next.config.js:\n```js\nexperimental: { workerThreads: false, cpus: 2 }\n```",
            timestamp=now + timedelta(minutes=5), has_code=True, reply_to="3",
        ),
        RawMessage(
            id="6", author_hash="ccc",
            content="omg that worked!! thanks so much",
            timestamp=now + timedelta(minutes=8), reply_to="5",
        ),
    ]


@pytest.fixture
def tech_thread() -> list[dict]:
    """A formatted technical thread (post-disentanglement)."""
    return [
        {
            "author_hash": "ccc123",
            "content": "Anyone seen this error with Next.js 14?\n```\nError: ENOMEM not enough memory\n```",
            "timestamp": "2026-02-22T14:02:00",
            "has_code": True,
            "has_mention": False,
            "reply_to": None,
        },
        {
            "author_hash": "ddd456",
            "content": "yeah that's an OOM during build, try reducing worker threads",
            "timestamp": "2026-02-22T14:04:00",
            "has_code": False,
            "has_mention": True,
            "reply_to": None,
        },
        {
            "author_hash": "ddd456",
            "content": "Try adding this to next.config.js:\n```js\nexperimental: { workerThreads: false, cpus: 2 }\n```",
            "timestamp": "2026-02-22T14:05:00",
            "has_code": True,
            "has_mention": False,
            "reply_to": "3",
        },
        {
            "author_hash": "ccc123",
            "content": "omg that worked!! thanks so much",
            "timestamp": "2026-02-22T14:08:00",
            "has_code": False,
            "has_mention": False,
            "reply_to": "5",
        },
    ]


@pytest.fixture
def noise_thread() -> list[dict]:
    """A noise thread (greetings only)."""
    return [
        {
            "author_hash": "aaa111",
            "content": "Hey everyone! Happy Monday",
            "timestamp": "2026-02-22T14:00:00",
            "has_code": False,
            "has_mention": False,
            "reply_to": None,
        },
        {
            "author_hash": "bbb222",
            "content": "gm gm",
            "timestamp": "2026-02-22T14:00:30",
            "has_code": False,
            "has_mention": False,
            "reply_to": None,
        },
    ]


@pytest.fixture
def high_quality_article() -> dict:
    """A compiled article that should pass the quality gate."""
    return {
        "article_type": "troubleshooting",
        "symptom": "Next.js 14 build fails with ENOMEM error when running next build on CI",
        "diagnosis": "Default Next.js build config spawns too many worker threads, exceeding available memory on constrained environments like CI/CD runners",
        "solution": "Disable experimental worker threads and limit CPU count in next.config.js. Step 1: Open next.config.js. Step 2: Add experimental section. Step 3: Rebuild.",
        "code_snippet": "// next.config.js\nmodule.exports = {\n  experimental: {\n    workerThreads: false,\n    cpus: 2\n  }\n}",
        "language": "javascript",
        "framework": "Next.js",
        "tags": ["next-js", "oom", "enomem", "build-error", "worker-threads", "memory"],
        "confidence": 0.92,
        "thread_summary": "Fix Next.js 14 ENOMEM build error by disabling worker threads",
        "source_url": None,
    }


@pytest.fixture
def low_quality_article() -> dict:
    """A compiled article that should fail the quality gate."""
    return {
        "article_type": "troubleshooting",
        "symptom": "error",
        "diagnosis": "bug",
        "solution": "fix it",
        "code_snippet": None,
        "language": "python",
        "framework": None,
        "tags": ["bug"],
        "confidence": 0.3,
        "thread_summary": "fix",
        "source_url": None,
    }
