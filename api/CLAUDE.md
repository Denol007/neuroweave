# API Backend

FastAPI application serving the NeuroWeave REST API, Celery task workers, and the LangGraph extraction pipeline.

## Structure

```
api/
├── main.py           — FastAPI app, middleware, lifespan
├── config.py         — pydantic-settings (reads .env)
├── deps.py           — Dependency injection (get_db, get_redis, get_current_user)
├── models/           — SQLAlchemy 2.0 ORM models
├── schemas/          — Pydantic request/response schemas
├── routers/          — API endpoint routers
├── services/         — Business logic + extraction pipeline
├── tasks/            — Celery async tasks
└── db/               — Database session + Alembic migrations
```

## Database

- PostgreSQL 16 with pgvector extension
- SQLAlchemy 2.0 async mode (asyncpg driver)
- Alembic for schema migrations
- All models in `api/models/`, each file = one table
- Vector columns: `messages.embedding` (vector(384)), `articles.embedding` (vector(1536))

## Patterns

- Repository pattern: models in `models/`, business logic in `services/`
- Dependency injection via FastAPI `Depends()`
- Pydantic schemas for all request/response bodies
- Async everywhere: `async def`, `await session.execute()`
- Structured logging with structlog

## API Endpoints

### Knowledge Base
- `GET /api/servers` — list public servers
- `GET /api/servers/{id}/articles` — articles for a server
- `GET /api/articles/{id}` — single article
- `GET /api/search?q=&server=` — hybrid search (vector + FTS)

### Server Management (Admin, Discord OAuth2)
- `POST /api/servers/{id}/channels` — set monitored channels
- `GET /api/servers/{id}/stats` — analytics
- `PATCH /api/articles/{id}/moderate` — hide/show article

### Consent
- `POST /api/consent` — record user consent
- `DELETE /api/consent/{user_hash}` — revoke + purge
- `GET /api/consent/{user_hash}` — check status

### Dataset Export
- `POST /api/datasets/export` — package + C2PA sign
- `GET /api/datasets` — list exports
- `GET /api/datasets/{id}/download` — download JSONL

### Auth & Payment
- `POST /api/webhooks/stripe` — Stripe webhook handler
- `GET /api/auth/discord` — OAuth2 redirect
- `GET /api/auth/discord/callback` — OAuth2 callback

## Environment Variables

```
DATABASE_URL, REDIS_URL, MONGODB_URI, ANTHROPIC_API_KEY,
DISCORD_BOT_TOKEN, DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET,
STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
LANGCHAIN_API_KEY, APP_SECRET_KEY, CORS_ORIGINS
```
