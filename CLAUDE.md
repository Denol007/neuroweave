# NeuroWeave — CTO Agent

You are the CTO of NeuroWeave. You manage the entire codebase, know every component, and execute tasks on command.

When the user says **"задание N"** (or "task N"), look up that task below, check its dependencies are done, and execute it fully — write all files, run setup commands, verify the result. If a dependency is not done, warn the user and say which task to run first.

After completing a task, **commit with conventional commit** and report what was done.

---

## Architecture

```
Discord → Bot (discord.py) → Redis Streams → Celery Worker
→ PII Anonymization (Llama 3.2 1B) → Disentanglement (Sentence-BERT)
→ LangGraph Pipeline (Router → Evaluator → Compiler → Quality Gate)
→ PostgreSQL + pgvector → Next.js Portal + Dataset Export (C2PA signed)
```

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic, Celery, Redis
- **Pipeline:** LangGraph (StateGraph), LangChain, Claude Haiku API, Pydantic v2
- **ML:** sentence-transformers (all-MiniLM-L6-v2, 384-dim), scikit-learn
- **Database:** PostgreSQL 16 + pgvector, MongoDB (LangGraph checkpoints), Redis Streams
- **Bot:** discord.py 2.x with app_commands
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS
- **DevOps:** Docker Compose, nginx, GitHub Actions

## Conventions

- Python: ruff format + ruff check, type hints on all functions
- All I/O operations are async (asyncpg, aiohttp, httpx)
- Config via pydantic-settings, everything through environment variables
- Logging: structlog with JSON output
- Tests: pytest + pytest-asyncio, fixtures in conftest.py
- Git: conventional commits — `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
- Imports: absolute from package root (`from api.models.article import Article`)
- No wildcard imports

## Key Decisions

- Claude Haiku (`claude-haiku-4-5-20251001`) for all LLM calls
- Sentence-BERT `all-MiniLM-L6-v2` for embeddings (384-dim)
- pgvector for semantic search
- MongoDBSaver for LangGraph checkpoints (prod), MemorySaver (dev)
- Redis Streams for message buffering with backpressure
- C2PA for digital provenance signing

## Architecture References

- `TECHNICAL_ARCHITECTURE.html` — full system architecture with diagrams
- `AGENTS_IMPLEMENTATION.html` — LangGraph pipeline implementation details

---

# TASK MAP

## Status tracking

After completing each task, add a ✅ next to it in this file so future sessions know what's done.

```
[✅] Task 1  — Database Layer
[✅] Task 2  — LangGraph Pipeline: State + Disentanglement
[✅] Task 3  — LangGraph Pipeline: Router + Evaluator
[✅] Task 4  — LangGraph Pipeline: Compiler + Quality Gate + Graph Assembly
[✅] Task 5  — FastAPI Core: App + Config + Auth
[✅] Task 6  — FastAPI Routers: Articles + Search + Consent
[✅] Task 7  — FastAPI Routers: Datasets + Servers + Stripe
[✅] Task 8  — Celery Tasks: Processing + Storage
[✅] Task 9  — Discord Bot: Core + Listener
[✅] Task 10 — Discord Bot: Commands (/privacy, /nw-ask)
[✅] Task 11 — Frontend: Next.js Setup + Layout
[✅] Task 12 — Frontend: Pages (servers, articles, search)
[✅] Task 13 — DevOps: Dockerfiles + Production Compose
[✅] Task 14 — DevOps: Nginx + GitHub Actions CI/CD
[✅] Task 15 — Tests: Pipeline Unit Tests
[✅] Task 16 — Tests: API Integration Tests
[✅] Task 17 — Tests: Bot + E2E
```

---

## Task 1 — Database Layer
**Domain:** Backend / Database
**Depends on:** nothing (first task)
**Files to create:**
- `api/db/session.py` — async engine, AsyncSession factory, get_db dependency
- `api/models/base.py` — declarative base with common mixins (id, created_at, updated_at)
- `api/models/server.py` — servers table (discord_id, name, icon_url, settings JSONB, plan enum)
- `api/models/channel.py` — channels table (FK→servers, discord_id, name, is_monitored)
- `api/models/message.py` — messages table (FK→channels, author_hash, content, embedding vector(384), timestamp)
- `api/models/thread.py` — threads table (FK→channels, message_ids array, status, cluster_metadata JSONB)
- `api/models/article.py` — articles table (FK→threads, symptom, diagnosis, solution, code_snippet, language, framework, tags array, confidence, thread_summary, embedding vector(1536), quality_score)
- `api/models/consent.py` — consent_records table (user_hash, server_id, kb_consent bool, ai_consent bool, granted_at, revoked_at)
- `api/models/dataset_export.py` — dataset_exports table (server_id, format, record_count, file_path, c2pa_manifest_hash, created_at)
- `api/models/__init__.py` — re-export all models
- Alembic init: `alembic.ini`, `api/db/migrations/env.py`, first migration
**Verify:** `docker compose up -d postgres` → `alembic upgrade head` succeeds → tables exist

---

## Task 2 — LangGraph Pipeline: State + Disentanglement
**Domain:** Pipeline
**Depends on:** Task 1 (needs model types for reference)
**Files to create:**
- `api/services/extraction/state.py` — AgentState TypedDict, ThreadMessage, EvaluationResult, CompiledArticle types
- `api/services/extraction/disentanglement.py` — DisentanglementEngine class: Sentence-BERT encoding, cosine similarity matrix, temporal clustering, BFS connected components. Params: threshold=0.75, temporal_window=4h, explicit link detection (@mentions, reply_to)
- `api/services/embeddings.py` — SentenceBERT wrapper: load model once, encode() method, batch support
**Verify:** can import and run `DisentanglementEngine().cluster(sample_messages)` — returns grouped threads

---

## Task 3 — LangGraph Pipeline: Router + Evaluator
**Domain:** Pipeline
**Depends on:** Task 2 (needs state.py)
**Files to create:**
- `api/services/extraction/nodes/router.py` — router_node function + ROUTER_SYSTEM_PROMPT + route_after_classification conditional. Claude Haiku, temp=0, max_tokens=100. Classifies NOISE/TECHNICAL. Default to TECHNICAL on ambiguity.
- `api/services/extraction/nodes/evaluator.py` — evaluator_node function + EVALUATOR_SYSTEM_PROMPT + route_after_evaluation conditional. Returns JSON: {has_solution, has_code, is_resolved, reasoning}. Resolved → compiler, else → END (checkpoint).
**Verify:** unit test with mocked LLM: router correctly returns classification, evaluator correctly parses JSON response

---

## Task 4 — LangGraph Pipeline: Compiler + Quality Gate + Graph Assembly
**Domain:** Pipeline
**Depends on:** Task 3 (needs router + evaluator)
**Files to create:**
- `api/services/extraction/nodes/compiler.py` — compiler_node function + ExtractedKnowledge Pydantic model + COMPILER_SYSTEM_PROMPT. Uses `ChatAnthropic.with_structured_output(ExtractedKnowledge)`. Handles validation errors gracefully.
- `api/services/extraction/nodes/quality_gate.py` — compute_quality_score heuristic (6 factors, max 1.0, threshold 0.7) + quality_gate_node + route_after_quality (pass/retry/reject, max 3 retries).
- `api/services/extraction/graph.py` — build_graph() function: StateGraph(AgentState), add all 5 nodes, set_entry_point("disentangle"), add_edge + add_conditional_edges for all routing, compile with checkpointer (MongoDB or Memory). Export `graph` instance.
**Verify:** full pipeline integration test with mocked LLM responses — state flows correctly through all nodes, quality gate triggers retry on low score

---

## Task 5 — FastAPI Core: App + Config + Auth
**Domain:** Backend API
**Depends on:** Task 1 (needs db session)
**Files to create:**
- `api/config.py` — Settings(BaseSettings) with all env vars, model_config for .env file
- `api/main.py` — FastAPI app, lifespan (startup/shutdown for DB), CORS middleware, exception handlers, include all routers
- `api/deps.py` — get_db (async session), get_redis, get_current_user (Discord OAuth2 JWT validation)
- `api/routers/auth.py` — GET /api/auth/discord (redirect), GET /api/auth/discord/callback (exchange code → JWT)
**Verify:** `uvicorn api.main:app` starts → GET /docs shows OpenAPI → /api/auth/discord redirects correctly

---

## Task 6 — FastAPI Routers: Articles + Search + Consent
**Domain:** Backend API
**Depends on:** Task 5 (needs app + deps)
**Files to create:**
- `api/schemas/article.py` — ArticleResponse, ArticleList, SearchResult Pydantic schemas
- `api/schemas/consent.py` — ConsentCreate, ConsentResponse schemas
- `api/routers/articles.py` — GET /api/servers/{id}/articles (paginated), GET /api/articles/{id}
- `api/routers/search.py` — GET /api/search?q=&server=&language=&tags= — hybrid search: pgvector cosine similarity + PostgreSQL FTS, combined ranking
- `api/routers/consent.py` — POST /api/consent, DELETE /api/consent/{user_hash} (revoke + cascade purge), GET /api/consent/{user_hash}
**Verify:** API tests with httpx — CRUD operations work, search returns ranked results

---

## Task 7 — FastAPI Routers: Datasets + Servers + Stripe
**Domain:** Backend API
**Depends on:** Task 6
**Files to create:**
- `api/schemas/server.py` — ServerResponse, ServerStats schemas
- `api/schemas/dataset.py` — DatasetExportRequest, DatasetExportResponse schemas
- `api/routers/servers.py` — GET /api/servers, POST /api/servers/{id}/channels, GET /api/servers/{id}/stats
- `api/routers/datasets.py` — POST /api/datasets/export (trigger Celery task), GET /api/datasets, GET /api/datasets/{id}/download
- `api/routers/webhooks.py` — POST /api/webhooks/stripe (verify signature, handle payment events)
- `api/services/c2pa_signer.py` — C2PA manifest creation stub (sign article hash with X.509)
**Verify:** all endpoints return correct responses, Stripe webhook signature validation works

---

## Task 8 — Celery Tasks: Processing + Storage
**Domain:** Backend / Task Queue
**Depends on:** Task 4 (pipeline) + Task 5 (app config)
**Files to create:**
- `api/celery_app.py` — Celery app instance, broker=REDIS_URL, result_backend
- `api/tasks/process_messages.py` — `process_message_batch` task: receive channel_id + messages, invoke LangGraph pipeline, handle results
- `api/tasks/generate_article.py` — `store_article` task: generate embedding, save to PostgreSQL, log metrics
- `api/tasks/export_dataset.py` — `export_dataset` task: query articles, package JSONL, C2PA sign, save file
**Verify:** Celery worker starts → can submit and execute a task → article stored in DB

---

## Task 9 — Discord Bot: Core + Listener
**Domain:** Discord Bot
**Depends on:** Task 8 (needs Celery tasks for triggering)
**Files to create:**
- `bot/main.py` — discord.py Client setup, intents (message_content, guilds, guild_messages), load cogs, run
- `bot/stream_producer.py` — RedisStreamProducer class: XADD to stream, batch trigger logic (50 msgs or 5 min)
- `bot/cogs/listener.py` — MessageListener cog: on_message → check if channel monitored → hash author ID (SHA-256) → publish to Redis Stream → trigger Celery batch when threshold reached
**Verify:** bot connects to Discord → sends message in monitored channel → message appears in Redis Stream

---

## Task 10 — Discord Bot: Commands
**Domain:** Discord Bot
**Depends on:** Task 9
**Files to create:**
- `bot/cogs/consent.py` — `/privacy` slash command: show consent options as ephemeral message with Buttons (KB consent, AI consent, revoke all), call API to store consent
- `bot/cogs/search.py` — `/nw-ask` slash command: take query param, call GET /api/search, format result as Discord embed with code block, send ephemeral
**Verify:** `/privacy` shows consent buttons → clicking stores consent via API → `/nw-ask nextjs oom` returns relevant article

---

## Task 11 — Frontend: Next.js Setup + Layout
**Domain:** Frontend
**Depends on:** Task 6 (needs API endpoints for data fetching)
**Files to create:**
- `web/package.json` — Next.js 14, TypeScript, Tailwind CSS, dependencies
- `web/next.config.js` — API rewrites for dev proxy
- `web/tsconfig.json`
- `web/tailwind.config.ts` — dark theme, custom colors matching NeuroWeave brand
- `web/app/globals.css` — Tailwind imports + base styles
- `web/app/layout.tsx` — root layout: dark theme, navigation bar, footer
- `web/components/Navbar.tsx` — logo, search input, nav links
- `web/components/Footer.tsx`
- `web/lib/api.ts` — fetch wrapper for backend API calls
**Verify:** `npm run dev` → page loads at localhost:3000 with dark theme and navigation

---

## Task 12 — Frontend: Pages
**Domain:** Frontend
**Depends on:** Task 11
**Files to create:**
- `web/app/page.tsx` — homepage: server grid with article counts, fetched via SSR
- `web/app/servers/[id]/page.tsx` — server articles page: article list with tag/language filters
- `web/app/articles/[id]/page.tsx` — article detail: symptom → diagnosis → solution → code block
- `web/app/search/page.tsx` — search results page with query input
- `web/components/ArticleCard.tsx` — card with title, tags, language badge, confidence
- `web/components/CodeBlock.tsx` — syntax highlighted code with copy button
- `web/components/SearchBar.tsx` — debounced search input
- `web/components/TagList.tsx` — clickable tag chips
**Verify:** navigate through all pages → articles render with code highlighting → search returns results

---

## Task 13 — DevOps: Dockerfiles + Production Compose
**Domain:** Infrastructure
**Depends on:** Tasks 5, 9, 11 (all apps exist)
**Files to create:**
- `infra/Dockerfile.api` — Python 3.12 slim, install deps, uvicorn with 4 workers
- `infra/Dockerfile.bot` — Python 3.12 slim, install deps, run bot + Celery worker
- `infra/Dockerfile.web` — Node 20, build Next.js standalone, serve
- `docker-compose.prod.yml` — all services (api, bot, web, postgres, redis, mongodb, nginx), volumes, healthchecks, restart policies
**Verify:** `docker compose -f docker-compose.prod.yml build` succeeds → `docker compose -f docker-compose.prod.yml up` all services healthy

---

## Task 14 — DevOps: Nginx + GitHub Actions CI/CD
**Domain:** Infrastructure
**Depends on:** Task 13
**Files to create:**
- `infra/nginx/nginx.conf` — reverse proxy (api.neuroweave.dev→:8000, neuroweave.dev→:3000), SSL placeholder, rate limiting 100/min, gzip, security headers
- `.github/workflows/ci.yml` — on push/PR: ruff check, pytest, next.js build
- `.github/workflows/deploy.yml` — on push to main: docker build + push to registry, SSH deploy
**Verify:** CI workflow syntax is valid (act or manual check), nginx config passes `nginx -t`

---

## Task 15 — Tests: Pipeline Unit Tests
**Domain:** Testing
**Depends on:** Task 4 (pipeline complete)
**Files to create:**
- `tests/conftest.py` — shared fixtures: mock LLM responses, sample messages, test DB session
- `tests/pipeline/test_disentanglement.py` — test clustering: 2 topics get separated, replies stay together, temporal window respected
- `tests/pipeline/test_router.py` — mock Claude response → verify NOISE/TECHNICAL classification + edge cases
- `tests/pipeline/test_evaluator.py` — mock Claude response → verify JSON parsing, resolved detection, cyclic routing
- `tests/pipeline/test_compiler.py` — mock structured output → verify Pydantic validation, error handling
- `tests/pipeline/test_quality_gate.py` — test scoring: high/low quality articles score correctly, retry logic works
- `tests/pipeline/test_graph_integration.py` — full graph with all mocked LLM nodes → verify end-to-end state flow
**Verify:** `pytest tests/pipeline/ -v` all pass

---

## Task 16 — Tests: API Integration Tests
**Domain:** Testing
**Depends on:** Task 7 (all API routers)
**Files to create:**
- `tests/api/test_articles.py` — CRUD operations, pagination, filtering
- `tests/api/test_search.py` — search endpoint, hybrid ranking
- `tests/api/test_consent.py` — create, check, revoke consent
- `tests/api/test_datasets.py` — export trigger, list, download
- `tests/api/test_auth.py` — OAuth2 flow, JWT validation
**Verify:** `pytest tests/api/ -v` all pass (uses test DB)

---

## Task 17 — Tests: Bot + E2E
**Domain:** Testing
**Depends on:** Task 10 (bot commands)
**Files to create:**
- `tests/bot/test_listener.py` — message capture, Redis XADD, author hashing
- `tests/bot/test_consent_cmd.py` — /privacy command response
- `tests/bot/test_search_cmd.py` — /nw-ask command response
**Verify:** `pytest tests/bot/ -v` all pass

---

# PHASE 2 — BUGFIXES & MISSING PIECES

These tasks fix critical bugs, add missing services, and make the project actually runnable end-to-end.

## Status tracking

```
[✅] Task 18 — BUGFIX: Embedding dimension mismatch (1536 → 384)
[✅] Task 19 — Infrastructure: Start Redis + MongoDB in dev compose
[✅] Task 20 — Bot: Load monitored channels from DB on startup
[✅] Task 21 — Seed data script + Makefile
[✅] Task 22 — PII Anonymizer service (anonymizer.py)
[✅] Task 23 — Consent enforcement in pipeline
[✅] Task 24 — Stripe webhook DB updates (remove TODOs)
[✅] Task 25 — Frontend: Login page + auth state
[✅] Task 26 — Frontend: Admin dashboard (channels, stats)
[✅] Task 27 — Frontend: Code syntax highlighting (shiki)
```

---

## Task 18 — BUGFIX: Embedding dimension mismatch
**Domain:** Database / Pipeline
**Depends on:** nothing
**Priority:** CRITICAL — blocks article storage at runtime
**Problem:** `articles.embedding` column is `vector(1536)` but `api/services/embeddings.py` uses `all-MiniLM-L6-v2` which outputs 384-dim vectors. pgvector will throw a dimension mismatch error when `store_article` tries to save.
**Fix:**
- Change `api/models/article.py`: `embedding = mapped_column(Vector(384))` (was 1536)
- Generate new Alembic migration: `alembic revision --autogenerate -m "fix article embedding dim 384"`
- Apply: `alembic upgrade head`
- Verify: `\d articles` shows `vector(384)`

---

## Task 19 — Infrastructure: Redis + MongoDB in dev compose
**Domain:** DevOps
**Depends on:** nothing
**Priority:** CRITICAL — Celery and LangGraph checkpoints need these
**Problem:** `docker-compose.yml` defines Redis + MongoDB but only Postgres was started. Also no app services for dev.
**Fix:**
- Ensure `docker compose up -d` starts all 3 (postgres, redis, mongodb)
- Add dev runner script or Makefile with commands to start API, Celery, Bot, Web
- Create `Makefile` with targets: `dev-infra`, `dev-api`, `dev-worker`, `dev-bot`, `dev-web`, `dev-all`
**Verify:** `docker compose up -d` → postgres:5432, redis:6379, mongodb:27017 all healthy

---

## Task 20 — Bot: Load monitored channels from DB
**Domain:** Discord Bot
**Depends on:** Task 19 (needs Redis running)
**Priority:** CRITICAL — without this, bot listens to nothing
**Problem:** `MessageListener._monitored_channels` is empty set, never populated. `set_monitored_channels()` exists but is never called.
**Fix:**
- In `bot/main.py` `on_ready`: fetch monitored channels from API (`GET /api/servers` → for each server, get channels where `is_monitored=True`)
- Call `listener_cog.set_monitored_channels(channel_ids)`
- Add periodic refresh (every 5 min) in case channels are updated via API
- Add API endpoint or use existing `GET /api/servers/{id}/stats` data
**Verify:** bot starts → logs "monitored_channels_updated count=N" → messages in those channels get published to Redis

---

## Task 21 — Seed data + Makefile
**Domain:** DevOps / Database
**Depends on:** Task 18 (needs correct embedding dim), Task 19 (needs all services)
**Priority:** HIGH — needed to test the full stack
**Fix:**
- Create `scripts/seed.py`: inserts 1 server, 2 channels, 5 sample messages, 2 threads, 1 article with embedding
- Create `Makefile`:
  ```
  dev-infra:   docker compose up -d
  dev-migrate: .venv/bin/alembic upgrade head
  dev-seed:    .venv/bin/python scripts/seed.py
  dev-api:     .venv/bin/uvicorn api.main:app --reload
  dev-worker:  .venv/bin/celery -A api.celery_app worker -l info -Q extraction,export
  dev-bot:     .venv/bin/python -m bot.main
  dev-web:     cd web && npm run dev
  dev-setup:   dev-infra dev-migrate dev-seed
  ```
**Verify:** `make dev-setup && make dev-api` → `curl localhost:8000/api/servers` returns seeded server

---

## Task 22 — PII Anonymizer
**Domain:** Pipeline / Privacy
**Depends on:** Task 21 (needs working pipeline)
**Priority:** HIGH — GDPR requirement, messages contain raw usernames/emails
**Problem:** `api/services/anonymizer.py` does not exist. Message content passes through pipeline with real names, emails, IPs intact.
**Fix:**
- Create `api/services/anonymizer.py`:
  - Regex pre-filters: email, IP, phone, URLs with usernames
  - Pattern: `@username` mentions in text → replace with `@[user_HASH]`
  - Pattern: file paths containing usernames `/Users/john/...` → `/Users/[REDACTED]/...`
  - For MVP: regex-only (no Llama 3.2 yet). Add Llama integration later.
- Integrate into `bot/stream_producer.py` or `api/tasks/process_messages.py`: anonymize content before pipeline
- Add tests in `tests/pipeline/test_anonymizer.py`
**Verify:** message "Hey john@gmail.com check 192.168.1.1" → "Hey [EMAIL] check [IP]"

---

## Task 23 — Consent enforcement in pipeline
**Domain:** Pipeline / Privacy
**Depends on:** Task 22 (anonymizer should run first)
**Priority:** HIGH — GDPR compliance
**Problem:** `process_messages.py` processes all messages regardless of user consent status. The consent API exists but is never checked.
**Fix:**
- In `api/tasks/process_messages.py` before invoking pipeline:
  - Query `consent_records` for each unique `author_hash` in the batch
  - Filter out messages from users who have NOT consented (or revoked)
  - Only pass consented messages to the pipeline
- Add `api/services/consent_checker.py` with `filter_consented_messages(messages, channel_id) → filtered_messages`
**Verify:** user without consent → their messages are excluded from pipeline input

---

## Task 24 — Stripe webhook DB updates
**Domain:** Backend / Payments
**Depends on:** nothing
**Priority:** MEDIUM — payments work but plans don't update
**Problem:** `api/routers/webhooks.py` has 3 TODO stubs — Stripe events are received and verified but Server.plan is never updated.
**Fix:**
- `checkout.session.completed` → find server by `metadata.server_id`, update `plan` to PRO
- `customer.subscription.updated` → update plan tier based on `price_id`
- `customer.subscription.deleted` → downgrade server to FREE
- Add `stripe_customer_id` field to Server model (new migration)
**Verify:** simulate webhook → server.plan changes in DB

---

## Task 25 — Frontend: Login page + auth state
**Domain:** Frontend
**Depends on:** nothing
**Priority:** MEDIUM — admin features need auth
**Fix:**
- `web/app/login/page.tsx` — "Login with Discord" button → redirects to `/api/auth/discord`
- `web/lib/auth.ts` — store JWT in localStorage, provide `useAuth()` hook
- `web/components/Navbar.tsx` — show login/logout button based on auth state
- `web/app/auth/callback/page.tsx` — handle OAuth callback, store token
**Verify:** click login → Discord OAuth → redirected back → Navbar shows username

---

## Task 26 — Frontend: Admin dashboard
**Domain:** Frontend
**Depends on:** Task 25 (needs auth)
**Priority:** MEDIUM
**Fix:**
- `web/app/dashboard/page.tsx` — server selector, channel toggle, stats overview
- `web/app/dashboard/[serverId]/page.tsx` — server management: toggle channels, view articles, moderate
- Uses `GET /api/servers/{id}/stats`, `POST /api/servers/{id}/channels`, `PATCH /api/articles/{id}/moderate`
**Verify:** logged-in admin can toggle channels on/off, see stats

---

## Task 27 — Frontend: Code syntax highlighting
**Domain:** Frontend
**Depends on:** nothing
**Priority:** LOW
**Problem:** `CodeBlock.tsx` renders plain `<pre><code>`, no highlighting.
**Fix:**
- Install `shiki` in web/
- Update `CodeBlock.tsx` to use shiki with dark theme
- Auto-detect language from article.language field
**Verify:** code blocks show colored syntax for JS/Python/Rust

---

# PHASE 3 — GITHUB DISCUSSIONS + MULTI-SOURCE PIPELINE

Expand beyond Discord: add GitHub Discussions as a data source, broaden pipeline to handle any content type (not just code/technical).

## Principles
- Articles don't require code to be created
- Content is NOT limited to "technical" — Q&A, guides, discussions are all valuable
- GitHub Discussions are already threaded → skip disentanglement
- Public GitHub data → skip consent check
- Backward compatible with Discord

## Status tracking

```
[✅] Task 28 — DB Schema: Source-Agnostic Generalization
[✅] Task 29 — Fix Hard Couplings (generate_article, consent_checker, export)
[✅] Task 30 — Pipeline: Broaden Router, Evaluator, Compiler for all content types
[✅] Task 31 — GitHub Discussions Fetcher (GraphQL API + Celery periodic)
[✅] Task 32 — API: GitHub Repo Management endpoints
[✅] Task 33 — Frontend: Source Badges + GitHub UI
[✅] Task 34 — Seed Data + CLI for GitHub sources
[✅] Task 35 — Tests: GitHub + expanded pipeline
```

---

## Task 28 — DB Schema: Source-Agnostic Generalization
**Domain:** Database
**Depends on:** nothing
**Priority:** CRITICAL
**Files to modify:**
- `api/models/server.py` — add `source_type` enum (discord/github/discourse), `external_id`, `source_url`, `source_metadata` JSONB
- `api/models/channel.py` — add `external_id`, make `discord_id` nullable
- `api/models/message.py` — add `external_id`, make `discord_message_id` nullable
- `api/models/article.py` — add `article_type` enum (troubleshooting/question_answer/guide/discussion_summary), `source_type`, `source_url`
- New Alembic migration: add columns → backfill → NOT NULL → unique constraints
**Verify:** `alembic upgrade head` succeeds, existing Discord data has `source_type='discord'` and `external_id` populated

---

## Task 29 — Fix Hard Couplings
**Domain:** Backend
**Depends on:** Task 28
**Files to modify:**
- `api/tasks/generate_article.py` — `Channel.discord_id` → `Channel.external_id`, add `source_type` param
- `api/tasks/process_messages.py` — pass `source_type`, skip consent for github
- `api/services/consent_checker.py` — `servers.discord_id` → `servers.external_id`, skip for github
- `api/tasks/export_dataset.py` — dynamic source string
**Verify:** `store_article(channel_id="DIC_kwDO123", source_type="github")` → article stored

---

## Task 30 — Pipeline: Broaden Router, Evaluator, Compiler
**Domain:** Pipeline
**Depends on:** Task 28
**Files to modify:**
- `api/services/extraction/state.py` — add `source_type`, `article_type`, `skip_disentangle` to AgentState
- `api/services/extraction/nodes/router.py` — 5 categories: NOISE/TROUBLESHOOTING/QUESTION_ANSWER/GUIDE/DISCUSSION_SUMMARY
- `api/services/extraction/nodes/evaluator.py` — Q&A passes without code, GUIDE/DISCUSSION always pass
- `api/services/extraction/nodes/compiler.py` — flexible ExtractedKnowledge (language optional, article_type, source_url)
- `api/services/extraction/nodes/quality_gate.py` — type-aware scoring (non-code articles not penalized)
- `api/services/extraction/graph.py` — skip_disentangle support
**Verify:** Q&A without code → quality ≥ 0.7; existing TROUBLESHOOTING unchanged

---

## Task 31 — GitHub Discussions Fetcher
**Domain:** Data Ingestion
**Depends on:** Task 28, Task 29
**Files to create:**
- `api/services/github_fetcher.py` — GitHubDiscussionsFetcher class (GraphQL API, fetch + convert to messages)
- `api/tasks/fetch_github_discussions.py` — Celery periodic task (15 min), fetch new discussions per github server
**Files to modify:**
- `api/config.py` — add GITHUB_TOKEN
- `api/celery_app.py` — register periodic task
**Verify:** Fetch discussions from `vercel/next.js`, pipeline produces articles with `source_type="github"`

---

## Task 32 — API: GitHub Repo Management
**Domain:** Backend API
**Depends on:** Task 31
**Files to create:**
- `api/schemas/github.py` — GitHubRepoCreate, GitHubRepoResponse
- `api/routers/github.py` — POST /api/github/repos, GET /api/github/repos, POST sync, DELETE
**Files to modify:**
- `api/routers/search.py` — add `source` filter param
- `api/schemas/article.py` — add article_type, source_type, source_url
- `api/schemas/server.py` — add source_type, external_id, source_url
- `api/main.py` — include github_router
**Verify:** POST repo → POST sync → GET search?source=github → articles appear

---

## Task 33 — Frontend: Source Badges + GitHub UI
**Domain:** Frontend
**Depends on:** Task 32
**Files to create:**
- `web/components/SourceBadge.tsx`, `web/components/ArticleTypeBadge.tsx`
- `web/app/dashboard/github/page.tsx`
**Files to modify:**
- `web/components/ArticleCard.tsx` — source + type badges
- `web/app/page.tsx` — mixed server/repo grid
- `web/app/articles/[id]/page.tsx` — "View on GitHub" link
- `web/app/search/page.tsx` — source filter dropdown
**Verify:** Homepage shows Discord + GitHub, articles have badges, search filters by source

---

## Task 34 — Seed Data + CLI for GitHub
**Domain:** DevOps
**Depends on:** Task 32
**Files to create:**
- `scripts/seed_github.py` — sample GitHub server + Q&A articles
- `scripts/fetch_github.py` — CLI: `python scripts/fetch_github.py vercel/next.js --limit 10`
**Verify:** `make dev-seed-github` → search returns GitHub articles

---

## Task 35 — Tests: GitHub + Expanded Pipeline
**Domain:** Testing
**Depends on:** Tasks 28-32
**Files to create:**
- `tests/pipeline/test_router_expanded.py` — 5 categories
- `tests/pipeline/test_evaluator_expanded.py` — Q&A без кода passes
- `tests/pipeline/test_compiler_expanded.py` — flexible article types
- `tests/pipeline/test_quality_gate_expanded.py` — non-code scores ≥ 0.7
- `tests/pipeline/test_github_fetcher.py` — GraphQL mock
- `tests/api/test_github.py` — CRUD endpoints
**Verify:** all new tests pass, existing 115 tests still pass
