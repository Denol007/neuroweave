# NeuroWeave

Decentralized platform for extracting, anonymizing, and licensing technical knowledge from Discord servers.

Discord conversations are automatically transformed into structured knowledge articles through an AI-powered pipeline: message clustering, noise filtering, resolution detection, and knowledge compilation — all with PII anonymization and GDPR consent enforcement.

## How It Works

```
Discord Messages → Bot → Redis Stream → Celery Worker
→ PII Anonymization → Thread Clustering (Sentence-BERT)
→ LangGraph Pipeline:
    Router (NOISE/TECHNICAL) → Evaluator (resolved?) → Compiler (structured output)
    → Quality Gate (score ≥ 0.7)
→ PostgreSQL + pgvector → Next.js Portal + Discord /nw-ask
```

## Features

- **AI Extraction Pipeline** — LangGraph StateGraph with 5 nodes, Claude Haiku LLM, cyclic evaluation, Pydantic structured output
- **Semantic Search** — Hybrid vector (pgvector) + full-text search (PostgreSQL FTS)
- **Discord Bot** — Auto-registers servers on join, `/privacy` consent UI, `/nw-ask` knowledge search
- **PII Anonymization** — Regex-based redaction of emails, IPs, phone numbers, API keys, file paths
- **GDPR Consent** — Users must opt-in via `/privacy` before their messages are processed
- **Admin Dashboard** — Server stats, article moderation, channel management
- **Digital Provenance** — C2PA manifest signing for dataset exports

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Celery |
| Pipeline | LangGraph, LangChain, Claude Haiku API, Pydantic v2 |
| ML | Sentence-BERT (all-MiniLM-L6-v2), scikit-learn |
| Database | PostgreSQL 16 + pgvector, MongoDB (checkpoints), Redis Streams |
| Bot | discord.py 2.x, slash commands |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shiki |
| DevOps | Docker Compose, nginx, GitHub Actions |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose

### 1. Clone & Install

```bash
git clone https://github.com/Denol007/neuroweave.git
cd neuroweave
make install
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
ANTHROPIC_API_KEY=sk-ant-your_key
```

#### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application → name it "NeuroWeave"
3. Bot tab → Reset Token → copy to `.env`
4. Enable **MESSAGE CONTENT INTENT** and **SERVER MEMBERS INTENT**
5. OAuth2 tab → copy Client ID and Client Secret to `.env`
6. Invite bot to your server:
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=68608&scope=bot%20applications.commands
   ```

### 3. Setup Infrastructure

```bash
make dev-setup
```

This starts PostgreSQL, Redis, MongoDB, runs migrations, and seeds sample data.

### 4. Run Everything

**Option A — All at once (background):**

```bash
make dev
```

All services start in the background. Logs in `.logs/`.

**Option B — Separate terminals (recommended for development):**

```bash
# Terminal 1 — API
make dev-api

# Terminal 2 — Celery Worker
make dev-worker

# Terminal 3 — Discord Bot
make dev-bot

# Terminal 4 — Frontend
make dev-web
```

### 5. Open

- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **Discord:** `/nw-ask react error` or `/privacy`

## Project Structure

```
api/                     FastAPI backend
├── models/              SQLAlchemy ORM models (7 tables)
├── routers/             API endpoints (17 routes)
├── schemas/             Pydantic request/response schemas
├── services/
│   ├── extraction/      LangGraph pipeline
│   │   ├── graph.py     StateGraph assembly
│   │   ├── state.py     AgentState TypedDict
│   │   ├── disentanglement.py  Sentence-BERT clustering
│   │   └── nodes/       Router, Evaluator, Compiler, Quality Gate
│   ├── anonymizer.py    PII redaction
│   ├── consent_checker.py  GDPR enforcement
│   ├── embeddings.py    Sentence-BERT wrapper
│   └── c2pa_signer.py   Digital provenance
├── tasks/               Celery async tasks
└── db/                  Database session + Alembic migrations

bot/                     Discord bot
├── main.py              Entry point + channel sync
├── stream_producer.py   Redis Streams publisher
└── cogs/
    ├── listener.py      Message capture + auto server registration
    ├── consent.py       /privacy slash command
    └── search.py        /nw-ask slash command

web/                     Next.js 14 frontend
├── app/                 Pages (home, search, articles, login, dashboard)
├── components/          UI components (Navbar, CodeBlock, ArticleCard, etc.)
└── lib/                 API client, auth context, syntax highlighting

infra/                   Docker, nginx, SQL
tests/                   115 tests (pipeline, API, bot)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/servers | List servers |
| GET | /api/servers/{id}/articles | Server articles (paginated) |
| GET | /api/servers/{id}/stats | Server analytics |
| POST | /api/servers/{id}/channels | Set monitored channels |
| GET | /api/articles/{id} | Article detail |
| PATCH | /api/articles/{id}/moderate | Hide/show article |
| GET | /api/search?q= | Hybrid search (vector + FTS) |
| POST | /api/consent | Record consent |
| GET | /api/consent/{hash} | Check consent |
| DELETE | /api/consent/{hash} | Revoke consent |
| POST | /api/datasets/export | Trigger dataset export |
| GET | /api/datasets | List exports |
| GET | /api/auth/discord | Discord OAuth2 |
| POST | /api/webhooks/stripe | Stripe payments |
| GET | /api/health | Health check |

## Pipeline Flow

```
1. Disentanglement  — Sentence-BERT clusters messages into threads
2. Router           — Claude Haiku classifies NOISE vs TECHNICAL
3. Evaluator        — Assesses if problem is resolved (cyclic)
4. Compiler         — Extracts structured knowledge (Pydantic schema)
5. Quality Gate     — Heuristic scorer, threshold 0.7, max 3 retries
```

## Commands

```bash
make install      # Install all dependencies
make dev-setup    # Start infra + migrate + seed
make dev          # Run all services (background)
make dev-stop     # Stop all services
make dev-logs     # Tail all logs
make test         # Run 115 tests
make lint         # Ruff check + format
make dev-reset    # Wipe all data and start fresh
```

## Tests

```bash
make test
# 115 passed in ~4s
```

Coverage: pipeline nodes, disentanglement, quality gate, API endpoints, bot listener, stream producer, consent, PII anonymizer.

## License

MIT
