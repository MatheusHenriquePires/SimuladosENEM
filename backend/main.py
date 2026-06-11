import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import CACHE_DIR, FRONTEND_DIR
from backend.routes import exams, export, ita

# 1. Resolvemos o caminho da raiz do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent

# 5. Inicialização da app sem lifespan que inicia threads
app = FastAPI(title="Plataforma de Simulados", version="1.1.0")

# Rotas
app.include_router(exams.router)
app.include_router(export.router)
app.include_router(ita.router)

# Ficheiros Estáticos (Frontend)
static_dir = FRONTEND_DIR / "src"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Ficheiros Estáticos (Cache do ENEM)
if CACHE_DIR.exists():
    app.mount("/cache-assets", StaticFiles(directory=CACHE_DIR), name="cache-assets")

# Ficheiros Estáticos (Imagens do ITA Brain)
ITA_BRAIN_DIR = ROOT_DIR / "ita-brain" 
if ITA_BRAIN_DIR.exists():
    app.mount("/ita-assets", StaticFiles(directory=ITA_BRAIN_DIR), name="ita-assets")

# Rota principal (Interface)
@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")