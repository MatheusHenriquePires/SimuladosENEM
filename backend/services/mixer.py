import itertools
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional
import random
from pathlib import Path

from backend.config import DAY_CADERNO_MAP, MIXES_DIR
from backend.models import MixedExam, MixedQuestion, MixRequest, Question
from backend.services.question_loader import get_available_years, load_exam

RANDOM_YEAR_COUNT = 3
CHUNK_SIZE = 5  # Tamanho do bloco para o restante da prova

logger = logging.getLogger(__name__)

async def build_mixed_exam(request: MixRequest) -> MixedExam:
    rng = secrets.SystemRandom()
    caderno = _draw_caderno(request.day)

    # Carrega os anos com fallback automático
    exams_by_year = await _load_years_with_fallback(
        request.day, caderno, request.language, rng
    )

    if len(exams_by_year) < 2:
        raise ValueError(
            "Não foi possível carregar questões de pelo menos 2 anos. "
            "Verifique sua conexão e tente novamente."
        )

    years = list(exams_by_year.keys())
    rng.shuffle(years)
    year_cycle = itertools.cycle(years)

    mixed_questions: list[MixedQuestion] = []
    
    # Define o índice base para encontrar a questão correta na lista carregada
    base_index = 1 if request.day == 1 else 91

    if request.day == 1:
        # TRATAMENTO ESPECIAL LÍNGUA ESTRANGEIRA (Questões 1 a 5)
        # Sorteia uma questão de cada ano, alternando
        for mixed_index in range(1, 6):
            source_year = next(year_cycle)
            source_question = exams_by_year[source_year][mixed_index - base_index]
            
            mixed_questions.append(
                MixedQuestion(
                    **source_question.model_dump(),
                    mixedIndex=mixed_index,
                    originalYear=source_year,
                    originalIndex=source_question.index,
                )
            )
        
        # O restante da prova do Dia 1 começará da questão 6
        start_index = 6
        end_index = 91
    else:
        # Se for o Dia 2, começa normalmente da 91
        start_index = 91
        end_index = 181

    # LÓGICA DE BLOCOS PARA O RESTANTE DA PROVA
    for chunk_start in range(start_index, end_index, CHUNK_SIZE):
        source_year = next(year_cycle)
        chunk_end = min(chunk_start + CHUNK_SIZE, end_index)

        for mixed_index in range(chunk_start, chunk_end):
            source_question = exams_by_year[source_year][mixed_index - base_index]
            
            mixed_questions.append(
                MixedQuestion(
                    **source_question.model_dump(),
                    mixedIndex=mixed_index,
                    originalYear=source_year,
                    originalIndex=source_question.index,
                )
            )

    exam_id = uuid.uuid4().hex[:12]
    mixed_exam = MixedExam(
        id=exam_id,
        years=years,
        caderno=caderno,
        language=request.language,
        day=request.day,
        questions=mixed_questions,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    
    _save_mix(mixed_exam)
    return mixed_exam


async def _load_years_with_fallback(
    day: int,
    caderno: str,
    language: str,
    rng: secrets.SystemRandom,
) -> dict[int, list[Question]]:
    """
    Tenta carregar RANDOM_YEAR_COUNT anos aleatórios.
    Se um ano falhar por qualquer motivo (PDF não encontrado, API indisponível,
    extração incompleta…), descarta silenciosamente e tenta o próximo da lista
    embaralhada — sem nunca travar a geração do simulado.
    """
    available_years, _, _ = get_available_years()
    if len(available_years) < 2:
        raise ValueError("São necessários pelo menos 2 anos disponíveis.")

    # Embaralha todos os anos para iterar sem repetição
    shuffled = rng.sample(available_years, len(available_years))

    loaded: dict[int, list[Question]] = {}
    failed: list[int] = []

    for year in shuffled:
        if len(loaded) >= RANDOM_YEAR_COUNT:
            break
        try:
            questions = await load_exam(year, caderno, language, day)
            loaded[year] = questions
            logger.info("Ano %d carregado com sucesso (%d questões).", year, len(questions))
        except Exception as exc:  # noqa: BLE001
            failed.append(year)
            logger.warning(
                "Ano %d ignorado (será substituído): %s", year, exc
            )

    if failed:
        logger.info(
            "Anos ignorados por falha: %s. Anos usados: %s.",
            failed,
            list(loaded.keys()),
        )

    return loaded


def _draw_caderno(day: int) -> str:
    return secrets.choice(tuple(DAY_CADERNO_MAP[day]))


def _save_mix(exam: MixedExam) -> None:
    path = MIXES_DIR / f"{exam.id}.json"
    path.write_text(
        exam.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_mix(exam_id: str) -> MixedExam:
    path = MIXES_DIR / f"{exam_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Simulado {exam_id} não encontrado.")
    return MixedExam.model_validate(json.loads(path.read_text(encoding="utf-8")))


def assemble_exam(questions: List[Dict], count: int = 30, materia: Optional[str] = None, seed: Optional[int] = None) -> Dict:
    """Monta uma prova simples escolhendo `count` questões aleatórias do conjunto fornecido.

    Se `materia` for informada, prioriza questões dessa matéria.
    Retorna um dicionário com metadados e lista ordenada de questões.
    """
    if seed is not None:
        random.seed(seed)

    pool = questions
    if materia:
        pool = [q for q in questions if materia.lower() in q.get('materia', '').lower()]
        if not pool:
            pool = questions

    chosen = random.sample(pool, k=min(count, len(pool)))

    exam = {
        "title": f"Prova montada - {materia or 'misto'}",
        "count_requested": count,
        "count_actual": len(chosen),
        "questions": chosen
    }
    return exam


def save_exam_json(exam: Dict, out_path: Optional[Path] = None) -> Path:
    if out_path is None:
        ROOT = Path(__file__).resolve().parent.parent
        out_path = ROOT / "ita-brain" / "assembled_exam.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(exam, indent=2, ensure_ascii=False), encoding='utf-8')
    return out_path