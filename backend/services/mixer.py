import json
import uuid
from datetime import datetime, timezone

from backend.config import MIXES_DIR
from backend.models import MixedExam, MixedQuestion, MixRequest, Question
from backend.services.question_loader import load_day1_exam


async def build_mixed_exam(request: MixRequest) -> MixedExam:
    exams_by_year: dict[int, list[Question]] = {}
    for year in request.years:
        exams_by_year[year] = await load_day1_exam(
            year, request.caderno, request.language
        )

    mixed_questions: list[MixedQuestion] = []
    years = request.years

    for mixed_index in range(1, 91):
        source_year = years[(mixed_index - 1) % len(years)]
        source_question = exams_by_year[source_year][mixed_index - 1]
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
        caderno=request.caderno,
        language=request.language,
        questions=mixed_questions,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    _save_mix(mixed_exam)
    return mixed_exam


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
