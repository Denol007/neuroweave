"""Seed script — populates the database with sample GitHub-sourced data.

Usage: python scripts/seed_github.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.config import settings
from api.models.article import Article
from api.models.channel import Channel
from api.models.server import Server, ServerPlan
from api.models.thread import Thread, ThreadStatus
from api.services.embeddings import encode

sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
engine = create_engine(sync_url)


def seed():
    with Session(engine) as db:
        # Check if GitHub server already exists
        existing = db.execute(
            text("SELECT id FROM servers WHERE external_id = 'vercel/next.js' AND source_type = 'github'")
        ).fetchone()
        if existing:
            print(f"GitHub seed data already exists (server id={existing[0]}). Skipping.")
            return

        # GitHub server (repo)
        server = Server(
            source_type="github",
            external_id="vercel/next.js",
            name="vercel/next.js",
            source_url="https://github.com/vercel/next.js/discussions",
            source_metadata={"owner": "vercel", "repo": "next.js", "categories": [
                {"id": "DIC_kwDOAZ_QA", "name": "Q&A"},
                {"id": "DIC_kwDOAZ_Ideas", "name": "Ideas"},
            ]},
            plan=ServerPlan.FREE,
        )
        db.add(server)
        db.flush()
        print(f"Created GitHub server: {server.name} (id={server.id})")

        # Categories as channels
        ch_qa = Channel(server_id=server.id, external_id="DIC_kwDOAZ_QA", name="Q&A", is_monitored=True)
        ch_ideas = Channel(server_id=server.id, external_id="DIC_kwDOAZ_Ideas", name="Ideas", is_monitored=True)
        db.add_all([ch_qa, ch_ideas])
        db.flush()
        print("Created channels: Q&A, Ideas")

        # Thread 1: Q&A article (no code)
        thread1 = Thread(
            channel_id=ch_qa.id,
            status=ThreadStatus.RESOLVED,
            message_ids=["D_kwDO_001", "DC_kwDO_002", "DC_kwDO_003"],
            cluster_metadata={"source": "github"},
        )
        db.add(thread1)
        db.flush()

        summary1 = "Best practices for structuring large Next.js App Router projects with multiple teams"
        embedding1 = encode(summary1).tolist()
        article1 = Article(
            thread_id=thread1.id,
            article_type="question_answer",
            source_type="github",
            source_url="https://github.com/vercel/next.js/discussions/99001",
            symptom="How should I structure a large Next.js 14 App Router project when multiple teams work on different features?",
            diagnosis="As Next.js projects grow with the App Router, the flat app/ directory can become chaotic. Teams need clear boundaries for ownership, independent deployments, and shared component libraries without stepping on each other's code.",
            solution="Use a Turborepo monorepo structure: each team owns a package in packages/ (e.g. packages/auth, packages/dashboard). Shared UI goes in packages/ui. Each deployable app lives in apps/. Route groups (parentheses) in app/ help organize within a single app. Use barrel exports and path aliases for clean imports between packages.",
            code_snippet=None,
            language="general",
            framework="Next.js",
            tags=["next-js", "app-router", "monorepo", "turborepo", "architecture", "team-structure"],
            confidence=0.88,
            thread_summary=summary1,
            quality_score=0.91,
            embedding=embedding1,
        )
        db.add(article1)

        # Thread 2: Guide article
        thread2 = Thread(
            channel_id=ch_ideas.id,
            status=ThreadStatus.RESOLVED,
            message_ids=["D_kwDO_004", "DC_kwDO_005"],
            cluster_metadata={"source": "github"},
        )
        db.add(thread2)
        db.flush()

        summary2 = "Understanding Next.js middleware: authentication, redirects, and A/B testing patterns"
        embedding2 = encode(summary2).tolist()
        article2 = Article(
            thread_id=thread2.id,
            article_type="guide",
            source_type="github",
            source_url="https://github.com/vercel/next.js/discussions/99002",
            symptom="Complete guide to Next.js middleware for common use cases",
            diagnosis="Next.js middleware runs at the edge before requests reach your pages. It intercepts requests at the CDN level, enabling authentication checks, geo-based redirects, A/B testing, and feature flags without server round-trips. Understanding when to use middleware vs API routes vs server components is key.",
            solution="Create middleware.ts in project root. Use NextResponse.redirect() for auth redirects, NextResponse.rewrite() for A/B testing (same URL, different content), and NextResponse.next() with modified headers for feature flags. Configure the matcher in config export to limit which routes trigger middleware. For auth: check JWT in cookies, redirect to /login if missing. For A/B: hash user cookie to assign variant, rewrite to /variant-a or /variant-b.",
            code_snippet="// middleware.ts\nimport { NextResponse } from 'next/server';\nimport type { NextRequest } from 'next/server';\n\nexport function middleware(request: NextRequest) {\n  const token = request.cookies.get('session');\n  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {\n    return NextResponse.redirect(new URL('/login', request.url));\n  }\n  return NextResponse.next();\n}\n\nexport const config = { matcher: ['/dashboard/:path*'] };",
            language="typescript",
            framework="Next.js",
            tags=["next-js", "middleware", "authentication", "edge-runtime", "a-b-testing", "redirects"],
            confidence=0.92,
            thread_summary=summary2,
            quality_score=0.95,
            embedding=embedding2,
        )
        db.add(article2)

        db.commit()
        print("Created 2 threads + 2 articles (Q&A + Guide) with embeddings")
        print()
        print("Seed complete! Try:")
        print("  curl http://localhost:8000/api/github/repos")
        print("  curl 'http://localhost:8000/api/search?q=nextjs+middleware&source=github'")


if __name__ == "__main__":
    seed()
