from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root so OPENAI_API_KEY and SurrealDB vars are set before app imports
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Agentic Auditor", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()

