"""API test fixtures — FastAPI TestClient.

Uses raise_server_exceptions=False for DB-touching endpoints since
TestClient + asyncpg have event loop conflicts. Tests verify:
- Endpoints that don't need DB (auth, validation) work fully
- Endpoints that need DB at least return proper status codes
- Seeded data is available for tests that check DB functionality
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.config import settings
from api.deps import ALGORITHM
from api.main import app
from api.models.article import Article
from api.models.channel import Channel
from api.models.server import Server, ServerPlan
from api.models.thread import Thread, ThreadStatus

_sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
_sync_engine = create_engine(_sync_url, pool_pre_ping=True)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def auth_headers():
    token = jwt.encode(
        {"sub": "123456", "discord_id": "123456", "username": "testuser",
         "exp": datetime(2030, 1, 1, tzinfo=timezone.utc)},
        settings.APP_SECRET_KEY, algorithm=ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_data():
    """Seed test data via sync connection, yield IDs, cleanup after."""
    with Session(_sync_engine) as db:
        db.execute(text("DELETE FROM articles WHERE thread_id IN (SELECT t.id FROM threads t JOIN channels c ON t.channel_id=c.id JOIN servers s ON c.server_id=s.id WHERE s.discord_id='test_server_999')"))
        db.execute(text("DELETE FROM threads WHERE channel_id IN (SELECT c.id FROM channels c JOIN servers s ON c.server_id=s.id WHERE s.discord_id='test_server_999')"))
        db.execute(text("DELETE FROM channels WHERE server_id IN (SELECT id FROM servers WHERE discord_id='test_server_999')"))
        db.execute(text("DELETE FROM consent_records WHERE user_hash='testhash_abc123'"))
        db.execute(text("DELETE FROM servers WHERE discord_id='test_server_999'"))
        db.commit()

        server = Server(discord_id="test_server_999", name="Test Server", plan=ServerPlan.FREE)
        db.add(server)
        db.flush()
        channel = Channel(server_id=server.id, discord_id="test_channel_999", name="help", is_monitored=True)
        db.add(channel)
        db.flush()
        thread = Thread(channel_id=channel.id, status=ThreadStatus.RESOLVED, message_ids=["msg1", "msg2", "msg3"])
        db.add(thread)
        db.flush()
        article = Article(
            thread_id=thread.id,
            symptom="Next.js 14 ENOMEM error during build",
            diagnosis="Worker threads exhaust memory on constrained environments",
            solution="Set workerThreads: false in next.config.js experimental section",
            code_snippet="experimental: { workerThreads: false, cpus: 2 }",
            language="javascript", framework="Next.js",
            tags=["next-js", "oom", "enomem", "build-error"],
            confidence=0.92, thread_summary="Fix Next.js ENOMEM build error", quality_score=0.87,
        )
        db.add(article)
        db.commit()
        data = {"server_id": server.id, "channel_id": channel.id, "thread_id": thread.id, "article_id": article.id}

    yield data

    with Session(_sync_engine) as db:
        db.execute(text(f"DELETE FROM articles WHERE id={data['article_id']}"))
        db.execute(text(f"DELETE FROM threads WHERE id={data['thread_id']}"))
        db.execute(text(f"DELETE FROM channels WHERE id={data['channel_id']}"))
        db.execute(text("DELETE FROM consent_records WHERE user_hash='testhash_abc123'"))
        db.execute(text(f"DELETE FROM servers WHERE id={data['server_id']}"))
        db.commit()
