.PHONY: up down logs build train-ai train-ai-discover ai-models-check ai-models-download test-backend test-frontend test-e2e test-load

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

build:
	docker compose build

train-ai-discover:
	python ai/training_pipeline/scripts/discover_datasets.py

train-ai:
	python ai/training_pipeline/scripts/run_training_pipeline.py --with-train

ai-models-check:
	python ai/scripts/model_budget.py --budget-gb 12

ai-models-download:
	python ai/scripts/model_budget.py --budget-gb 12 --download

test-backend:
	cd backend && python -m pytest -q

test-frontend:
	npm --prefix frontend run lint
	npm --prefix frontend run typecheck
	npm --prefix frontend run build

test-e2e:
	cd tests/e2e && npm install && npm run install:browsers && npm test

test-load:
	k6 run tests/load/k6-smoke.js
