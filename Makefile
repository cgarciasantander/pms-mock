.PHONY: run dev up down docker migrate downgrade revision seed test lint format install

install:
	pip install -e ".[dev]"

# ── API ───────────────────────────────────────────────────────────────────────
run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn app.main:app --reload --port 8000

# ── Docker ────────────────────────────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

docker:
	docker compose --profile api up --build -d

# ── Database migrations ───────────────────────────────────────────────────────
migrate:
	alembic upgrade head

downgrade:
	alembic downgrade -1

# Usage: make revision MSG="add guest nationality"
revision:
	alembic revision --autogenerate -m "$(MSG)"

seed:
	python -m scripts.seed

# ── Quality ───────────────────────────────────────────────────────────────────
test:
	pytest --cov=app --cov-report=term-missing --cov-report=html

lint:
	ruff check app tests

format:
	ruff format app tests
