from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
PDF_DIR = DATA_DIR / "pdfs"
MIXES_DIR = DATA_DIR / "mixes"
FRONTEND_DIR = ROOT_DIR / "frontend"

ENEM_API_BASE = "https://api.enem.dev/v1"
INEP_DOWNLOAD_BASE = "https://download.inep.gov.br/enem/provas_e_gabaritos"
INEP_PAGE_BASE = (
    "https://www.gov.br/inep/pt-br/areas-de-atuacao/"
    "avaliacao-e-exames-educacionais/enem/provas-e-gabaritos"
)

API_YEARS = range(2009, 2024)
PDF_YEARS = range(2024, 2026)

CADERNO_MAP = {
    "azul": 1,
    "amarelo": 2,
    "branco": 3,
    "verde": 4,
}

DAY_CADERNO_MAP = {
    1: CADERNO_MAP,
    2: {
        "amarelo": 5,
        "cinza": 6,
        "azul": 7,
        "rosa": 8,
    },
}

CADERNO_LABELS = {v: k.capitalize() for k, v in CADERNO_MAP.items()}

for directory in (CACHE_DIR, PDF_DIR, MIXES_DIR):
    directory.mkdir(parents=True, exist_ok=True)
