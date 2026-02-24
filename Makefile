.PHONY: install dev-infra dev-migrate dev-seed dev-seed-github dev-setup dev-api dev-worker dev-bot dev-web dev dev-stop test lint dev-down dev-reset fetch-github

# --- First-time setup ---
install:
	@echo "📦 Installing Python 3.12 dependencies..."
	python3.12 -m venv .venv || python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install hatchling
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/pip install psycopg2-binary
	@echo "📦 Installing Node.js dependencies..."
	cd web && npm install
	@echo "✅ All dependencies installed"

# --- Infrastructure ---
dev-infra:
	docker compose up -d
	@echo "⏳ Waiting for services..."
	@sleep 3
	@docker compose ps

dev-migrate:
	.venv/bin/alembic upgrade head

dev-seed:
	.venv/bin/python scripts/seed.py

dev-seed-github:
	.venv/bin/python scripts/seed_github.py

fetch-github:
	.venv/bin/python scripts/fetch_github.py $(ARGS)

dev-setup: dev-infra dev-migrate dev-seed dev-seed-github
	@echo ""
	@echo "✅ Infrastructure ready!"
	@echo "   Postgres: localhost:5432"
	@echo "   Redis:    localhost:6379"
	@echo "   MongoDB:  localhost:27017"
	@echo ""
	@echo "Run 'make dev' to start all services"

# --- Run all services (background) ---
dev: dev-stop
	@echo "🚀 Starting all services..."
	@mkdir -p .logs
	.venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000 > .logs/api.log 2>&1 & echo $$! > .pids/api.pid
	@sleep 2
	.venv/bin/celery -A api.celery_app worker --loglevel=info -Q extraction,export --concurrency=2 > .logs/worker.log 2>&1 & echo $$! > .pids/worker.pid
	.venv/bin/python -m bot.main > .logs/bot.log 2>&1 & echo $$! > .pids/bot.pid
	cd web && npm run dev > ../.logs/web.log 2>&1 & echo $$! > .pids/web.pid
	@sleep 3
	@echo ""
	@echo "✅ All services running!"
	@echo "   🌐 Frontend:  http://localhost:3000"
	@echo "   🔌 API:       http://localhost:8000"
	@echo "   📖 API Docs:  http://localhost:8000/docs"
	@echo "   🤖 Bot:       NeuroWeave (Discord)"
	@echo "   📋 Logs:      .logs/"
	@echo ""
	@echo "Run 'make dev-stop' to stop all services"
	@echo "Run 'make dev-logs' to tail all logs"

dev-stop:
	@mkdir -p .pids
	@-kill $$(cat .pids/api.pid 2>/dev/null) 2>/dev/null || true
	@-kill $$(cat .pids/worker.pid 2>/dev/null) 2>/dev/null || true
	@-kill $$(cat .pids/bot.pid 2>/dev/null) 2>/dev/null || true
	@-kill $$(cat .pids/web.pid 2>/dev/null) 2>/dev/null || true
	@-kill $$(lsof -ti:3000) 2>/dev/null || true
	@-kill $$(lsof -ti:8000) 2>/dev/null || true
	@rm -f .pids/*.pid

dev-logs:
	@tail -f .logs/*.log

# --- Run services individually (foreground, for separate terminals) ---
dev-api:
	.venv/bin/uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-worker:
	PYTORCH_MPS_DISABLE=1 TOKENIZERS_PARALLELISM=false .venv/bin/celery -A api.celery_app worker --beat --loglevel=info -Q extraction,export --pool=solo

dev-bot:
	.venv/bin/python -m bot.main

dev-web:
	cd web && npm run dev

# --- Quality ---
test:
	.venv/bin/pytest tests/ -v

lint:
	.venv/bin/ruff check api/ bot/ tests/
	.venv/bin/ruff format --check api/ bot/ tests/

# --- Cleanup ---
dev-down:
	docker compose down

dev-reset: dev-stop dev-down
	docker volume rm startup_postgres_data startup_redis_data startup_mongo_data 2>/dev/null || true
	@echo "All data wiped. Run 'make dev-setup' to start fresh."
