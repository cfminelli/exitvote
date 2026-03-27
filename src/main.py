"""
ExitVote API — entry point.

FastAPI auto-generates interactive docs at /docs (Swagger UI).
Open that in your browser to try every endpoint without any extra tool.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.database import init_db
from src.routes import rooms, votes

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ExitVote",
    description="Anonymous event exit voting. Join a room, vote Stay or Leave, see live results.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(rooms.router)
app.include_router(votes.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
