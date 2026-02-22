# Infrastructure

Docker, nginx, and CI/CD configuration for NeuroWeave.

## Docker Services (Production)

| Service | Image | Port |
|---------|-------|------|
| api | Dockerfile.api (FastAPI + Uvicorn, 4 workers) | 8000 |
| bot | Dockerfile.bot (discord.py + Celery worker) | — |
| web | Dockerfile.web (Next.js standalone) | 3000 |
| postgres | pgvector/pgvector:pg16 | 5432 |
| redis | redis:7-alpine | 6379 |
| mongodb | mongo:7 | 27017 |
| nginx | nginx:alpine | 80, 443 |

## Nginx

- Reverse proxy: `api.neuroweave.dev` → `:8000`, `neuroweave.dev` → `:3000`
- SSL via Let's Encrypt (certbot)
- Rate limiting: 100 req/min per IP for API
- WebSocket passthrough for Discord bot health checks

## CI/CD (GitHub Actions)

- `ci.yml` — on push/PR: ruff check, pytest, Next.js build
- `deploy.yml` — on push to main: docker build, push to registry, deploy

## Volumes

- `/data/postgres` — persistent database
- `/data/redis` — persistent cache/streams
- `/data/exports` — JSONL dataset files

## External Services

- Anthropic API (Claude Haiku)
- Stripe Connect
- AWS KMS (C2PA signing)
- Sentry (error tracking)
- LangSmith (LLM observability)
