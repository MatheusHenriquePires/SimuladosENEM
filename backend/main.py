from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import CACHE_DIR, FRONTEND_DIR
from backend.routes import exams, export

app = FastAPI(title="ENEM Mesclador", version="1.0.0")

app.include_router(exams.router)
app.include_router(export.router)

static_dir = FRONTEND_DIR / "src"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

if CACHE_DIR.exists():
    app.mount("/cache-assets", StaticFiles(directory=CACHE_DIR), name="cache-assets")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
