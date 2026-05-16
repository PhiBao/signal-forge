.PHONY: setup backend frontend cycle

setup:
	pip install -r requirements.txt
	cd frontend && pnpm install

backend:
	uv run uvicorn agents.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && pnpm dev

cycle:
	uv run python -c "import asyncio; from agents.orchestrator import Orchestrator; asyncio.run(Orchestrator().run_cycle())"
