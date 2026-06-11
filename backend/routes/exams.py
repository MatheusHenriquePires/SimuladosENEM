from fastapi import APIRouter, HTTPException

from backend.config import DAY_CADERNO_MAP
from backend.models import MixRequest, SyncResponse, YearsResponse
from backend.services.mixer import build_mixed_exam
from backend.services.question_loader import get_available_years, sync_year

router = APIRouter(prefix="/api", tags=["exams"])


@router.get("/years", response_model=YearsResponse)
async def list_years() -> YearsResponse:
    all_years, api_years, pdf_years = get_available_years()
    return YearsResponse(years=all_years, apiYears=api_years, pdfYears=pdf_years)


@router.post("/mix")
async def create_mix(request: MixRequest):
    try:
        return await build_mixed_exam(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync/{year}", response_model=SyncResponse)
async def sync_exam_year(
    year: int,
    caderno: str = "azul",
    language: str = "ingles",
    day: int = 1,
) -> SyncResponse:
    if day not in DAY_CADERNO_MAP:
        raise HTTPException(status_code=400, detail="Dia invalido.")
    if caderno not in DAY_CADERNO_MAP[day]:
        raise HTTPException(status_code=400, detail="Caderno invalido para o dia escolhido.")
    if language not in {"ingles", "espanhol"}:
        raise HTTPException(status_code=400, detail="Idioma invalido.")

    try:
        questions, source = await sync_year(year, caderno, language, day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SyncResponse(
        year=year,
        caderno=caderno,
        language=language,
        questionCount=len(questions),
        source=source,
    )
