dev-app:
	make dev-backend & make dev-frontend

dev-backend:
	uv run adk api_server --allow_origins="*"

dev-frontend:
	uv run streamlit run frontend/app.py

install:
	uv sync --frozen 