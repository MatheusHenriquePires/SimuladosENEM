from pathlib import Path
from typing import Optional

# Arquivo de controle para parar workers
ROOT_DIR = Path(__file__).resolve().parent.parent
STOP_FILE = ROOT_DIR / "STOP_WORKERS"


def should_stop() -> bool:
    """Retorna True se existir o arquivo de parada."""
    return STOP_FILE.exists()


def create_stop_file(text: Optional[str] = None) -> Path:
    """Cria o arquivo de parada (graceful stop)."""
    STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    STOP_FILE.write_text(text or "stop", encoding='utf-8')
    return STOP_FILE


def remove_stop_file() -> bool:
    """Remove o arquivo de parada, retornando True se removido."""
    if STOP_FILE.exists():
        STOP_FILE.unlink()
        return True
    return False


def stop_file_path() -> Path:
    return STOP_FILE
