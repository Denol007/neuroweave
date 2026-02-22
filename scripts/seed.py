"""Seed script — populates the database with sample data for development.

Usage: python scripts/seed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.config import settings
from api.models.article import Article
from api.models.channel import Channel
from api.models.message import Message
from api.models.server import Server, ServerPlan
from api.models.thread import Thread, ThreadStatus
from api.services.embeddings import encode

sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
engine = create_engine(sync_url)


def seed():
    with Session(engine) as db:
        # Check if already seeded
        existing = db.execute(text("SELECT count(*) FROM servers")).scalar()
        if existing > 0:
            print(f"Database already has {existing} server(s). Skipping seed.")
            print("Run 'make dev-reset && make dev-setup' to start fresh.")
            return

        # Server
        server = Server(
            discord_id="1234567890",
            name="React Community",
            icon_url=None,
            member_count=15420,
            plan=ServerPlan.FREE,
        )
        db.add(server)
        db.flush()
        print(f"Created server: {server.name} (id={server.id})")

        # Channels
        ch_help = Channel(server_id=server.id, discord_id="1111111111", name="help", is_monitored=True)
        ch_general = Channel(server_id=server.id, discord_id="2222222222", name="general", is_monitored=False)
        db.add_all([ch_help, ch_general])
        db.flush()
        print(f"Created channels: help (monitored), general")

        # Thread 1: resolved
        thread1 = Thread(
            channel_id=ch_help.id,
            status=ThreadStatus.RESOLVED,
            message_ids=["msg1", "msg2", "msg3", "msg4"],
            cluster_metadata={"source": "seed"},
        )
        db.add(thread1)
        db.flush()

        # Article 1
        summary1 = "Fix Next.js 14 ENOMEM build error by disabling worker threads"
        embedding1 = encode(summary1).tolist()
        article1 = Article(
            thread_id=thread1.id,
            symptom="Next.js 14 build fails with ENOMEM (out of memory) error during `next build` on CI/CD runners with limited RAM",
            diagnosis="Default Next.js build configuration spawns multiple worker threads for parallel compilation. On constrained environments (2GB RAM CI runners, small VPS), this exceeds available memory causing the fork() system call to fail with ENOMEM.",
            solution="1. Open next.config.js\n2. Add experimental section to disable worker threads\n3. Limit CPU count to reduce parallel compilation\n4. Rebuild the project",
            code_snippet="// next.config.js\nmodule.exports = {\n  experimental: {\n    workerThreads: false,\n    cpus: 2\n  }\n}",
            language="javascript",
            framework="Next.js",
            tags=["next-js", "oom", "enomem", "build-error", "worker-threads", "memory"],
            confidence=0.92,
            thread_summary=summary1,
            quality_score=0.87,
            embedding=embedding1,
        )
        db.add(article1)

        # Thread 2: resolved
        thread2 = Thread(
            channel_id=ch_help.id,
            status=ThreadStatus.RESOLVED,
            message_ids=["msg5", "msg6", "msg7"],
            cluster_metadata={"source": "seed"},
        )
        db.add(thread2)
        db.flush()

        # Article 2
        summary2 = "Fix React hydration mismatch error with useEffect for client-only rendering"
        embedding2 = encode(summary2).tolist()
        article2 = Article(
            thread_id=thread2.id,
            symptom="React throws 'Text content does not match server-rendered HTML' hydration error when using browser APIs like window.innerWidth in component body",
            diagnosis="Server-side rendering (SSR) runs on Node.js where browser APIs like `window` don't exist. When the component renders different content on server vs client, React detects the mismatch during hydration.",
            solution="1. Move browser-dependent logic into a useEffect hook\n2. Use a state variable initialized to a safe default\n3. Update state in useEffect (runs only on client)\n4. Optionally use dynamic() with ssr: false for entire components",
            code_snippet="const [width, setWidth] = useState(0);\n\nuseEffect(() => {\n  setWidth(window.innerWidth);\n  const handleResize = () => setWidth(window.innerWidth);\n  window.addEventListener('resize', handleResize);\n  return () => window.removeEventListener('resize', handleResize);\n}, []);",
            language="javascript",
            framework="React",
            tags=["react", "hydration", "ssr", "next-js", "useeffect", "window"],
            confidence=0.88,
            thread_summary=summary2,
            quality_score=0.82,
            embedding=embedding2,
        )
        db.add(article2)

        db.commit()
        print(f"Created 2 threads + 2 articles with embeddings")
        print()
        print("Seed complete! Try:")
        print("  curl http://localhost:8000/api/servers")
        print("  curl http://localhost:8000/api/servers/1/articles")
        print("  curl 'http://localhost:8000/api/search?q=nextjs+memory+error'")


if __name__ == "__main__":
    seed()
