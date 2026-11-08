.PHONY: dev demo demo-local up down seed test bench validate dashboard run-mocks run-backend

dev:
	python scripts/run_all.py

demo:
	docker compose up --build

demo-local:
	python scripts/seed_data.py && streamlit run apps/web/dashboard.py

up:
	docker compose up --build -d

down:
	docker compose down

seed:
	python scripts/seed_data.py

test:
	pytest tests/ -q --tb=short

bench:
	python scripts/bench.py

validate:
	python scripts/validate.py

dashboard:
	streamlit run apps/web/dashboard.py

run-mocks:
	uvicorn mocks.main:app --port 8001 --reload

run-backend:
	cd backend && uvicorn app.main:app --port 8000 --reload
