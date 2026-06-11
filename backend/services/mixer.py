import json
import secrets
import uuid
from datetime import datetime, timezone

from backend.config import DAY_CADERNO_MAP, MIXES_DIR
from backend.models import MixedExam, MixedQuestion, MixRequest, Question
from backend.services.question_loader import get_available_years, load_exam

RANDOM_YEAR_COUNT = 3


async def build_mixed_exam(request: MixRequest) -> MixedExam:
    rng = secrets.SystemRandom()
    years = _draw_years()
    caderno = _draw_caderno(request.day)

    exams_by_year: dict[int, list[Question]] = {}
    for year in years:
        exams_by_year[year] = await load_exam(
            year, caderno, request.language, request.day
        )

    mixed_questions: list[MixedQuestion] = []
    start_index = 1 if request.day == 1 else 91
    end_index = start_index + 90

    for mixed_index in range(start_index, end_index):
        source_year = rng.choice(years)
        source_question = exams_by_year[source_year][mixed_index - start_index]
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


def _draw_years() -> list[int]:
    available_years, _, _ = get_available_years()
    if len(available_years) < 2:
        raise ValueError("Sao necessarios pelo menos 2 anos disponiveis.")

    rng = secrets.SystemRandom()
    count = min(RANDOM_YEAR_COUNT, len(available_years))
    return rng.sample(available_years, count)


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
        raise FileNotFoundError(f"Simulado {exam_id} nao encontrado.")
    return MixedExam.model_validate(json.loads(path.read_text(encoding="utf-8")))
