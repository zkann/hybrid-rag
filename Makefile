.PHONY: install db-up db-down schema seed serve test package clean

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -r requirements.txt
	$(PIP) install -q pytest

db-up:
	docker compose up -d
	@echo "waiting for postgres..."
	@until docker compose exec -T db pg_isready -U rag -d rag >/dev/null 2>&1; do sleep 1; done
	@echo "postgres ready on localhost:5432"

db-down:
	docker compose down

schema:
	psql "postgresql://rag:rag@localhost:5433/rag" -f sql/001_schema.sql

seed:
	bash scripts/seed_corpus.sh
	$(PY) -m scripts.ingest_docs --dir docs_corpus

serve:
	$(VENV)/bin/uvicorn app.main:app --reload --port 8000

test:
	$(VENV)/bin/pytest -q

package:
	rm -rf build dist && mkdir -p dist
	$(PIP) install -q -r requirements.txt -t build/
	cp -r app build/
	cd build && zip -qr ../dist/lambda.zip . -x '*.pyc'
	@echo "built dist/lambda.zip"

clean:
	rm -rf build dist .pytest_cache
