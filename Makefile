.PHONY: up down seed test bench validate lint

up:
	docker compose up --build -d

down:
	docker compose down

seed:
	cd backend && python scripts/seed_data.py

test:
	cd backend && pytest tests/ -v --tb=short

bench:
	cd backend && python scripts/bench.py

validate:
	cd backend && python scripts/validate.py

lint:
	cd backend && ruff check . && mypy app/ core/ --ignore-missing-imports

migrate:
	cd backend && alembic upgrade head
