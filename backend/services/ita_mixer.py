import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

from backend.config import MIXES_DIR
from backend.models import ItaMixedExam, ItaMixedQuestion, ItaMixRequest
from .mixer import assemble_exam, save_exam_json

# Define o caminho para a pasta ita-brain na raiz do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ITA_DIR = ROOT_DIR / "ita-brain" # Certifique-se que a pasta se chama "ita-brain"
ITA_JSONL_FILE = ITA_DIR /"banco_questoes_transcrito.json"

QUESTIONS_PER_EXAM = 15

def _load_ita_bank() -> list[dict]:
    if not ITA_JSONL_FILE.exists():
        raise FileNotFoundError(f"Arquivo {ITA_JSONL_FILE} não encontrado. Coloque a pasta do ita-brain na raiz do projeto.")
    
    questions = []
    with open(ITA_JSONL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    return questions

async def build_ita_mixed_exam(request: ItaMixRequest) -> ItaMixedExam:
    bank = _load_ita_bank()
    
    # Filtra as questões pela fase solicitada
    filtered_bank = [q for q in bank if q.get("fase") == request.phase]
    
    # Filtra pela disciplina
    if request.subject != "todas":
        filtered_bank = [q for q in filtered_bank if q.get("materia") == request.subject]
        
    if len(filtered_bank) < QUESTIONS_PER_EXAM:
        raise ValueError(f"Não há questões suficientes. Encontradas: {len(filtered_bank)}. Necessárias: {QUESTIONS_PER_EXAM}.")

    # Sorteia as questões
    rng = secrets.SystemRandom()
    selected_questions = rng.sample(filtered_bank, QUESTIONS_PER_EXAM)
    
    mixed_questions = []
    for i, q in enumerate(selected_questions, start=1):
        mixed_questions.append(ItaMixedQuestion(**q, mixedIndex=i))

    exam_id = uuid.uuid4().hex[:12]
    mixed_exam = ItaMixedExam(
        id=exam_id,
        subject=request.subject,
        phase=request.phase,
        questions=mixed_questions,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    
    MIXES_DIR.mkdir(parents=True, exist_ok=True)
    mix_path = MIXES_DIR / f"ita-{exam_id}.json"
    mix_path.write_text(mixed_exam.model_dump_json(indent=2), encoding="utf-8")
    
    return mixed_exam

def assemble_ita_prova(questions: List[Dict], by_materia: Optional[str] = None, total_questions: int = 30, seed: Optional[int] = None) -> Dict:
    """Regra simples para montar uma prova no estilo ITA.

    Atualmente: chama assemble_exam priorizando a matéria (se informada).
    Pode ser estendida com regras de competências/fases.
    """
    exam = assemble_exam(questions, count=total_questions, materia=by_materia, seed=seed)
    return exam