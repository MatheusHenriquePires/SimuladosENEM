import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

from backend.config import (
    API_YEARS,
    CACHE_DIR,
    CADERNO_MAP,
    ENEM_API_BASE,
    PDF_YEARS,
)
from backend.models import Alternative, Question
from backend.services.inep_client import download_exam_pdfs

DAY1_QUESTION_COUNT = 90


def _cache_path(year: int, caderno: str, language: str) -> Path:
    cache_dir = CACHE_DIR / str(year)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"dia1-{caderno}-{language}.json"


def _normalize_api_question(data: dict, language: str) -> Question | None:
    question_language = data.get("language")
    index = data.get("index", 0)

    if index <= 5 and question_language and question_language != language:
        return None

    alternatives = [
        Alternative(
            letter=alt["letter"],
            text=alt.get("text") or "",
            isCorrect=alt.get("isCorrect", False),
            file=alt.get("file"),
        )
        for alt in data.get("alternatives", [])
    ]

    return Question(
        year=data["year"],
        index=index,
        discipline=data.get("discipline") or "linguagens",
        language=question_language or language,
        context=data.get("context") or "",
        alternativesIntroduction=data.get("alternativesIntroduction") or "",
        alternatives=alternatives,
        correctAlternative=data.get("correctAlternative") or "",
        files=[f for f in data.get("files", []) if f],
        source="enem-api",
    )


async def _fetch_api_question(
    client: httpx.AsyncClient, year: int, index: int, language: str
) -> Question | None:
    url = f"{ENEM_API_BASE}/exams/{year}/questions/{index}"
    params = {"language": language} if index <= 5 else None
    try:
        response = await client.get(url, params=params)
        if response.status_code == 404 and index <= 5:
            response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    return _normalize_api_question(response.json(), language)


async def _load_from_api(year: int, language: str) -> list[Question]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [
            _fetch_api_question(client, year, index, language)
            for index in range(1, DAY1_QUESTION_COUNT + 1)
        ]
        results = await asyncio.gather(*tasks)

    questions: list[Question] = []
    missing: list[int] = []
    for index, result in enumerate(results, start=1):
        if result is None:
            missing.append(index)
            continue
        questions.append(result)

    if missing:
        raise ValueError(
            f"API incompleta para ENEM {year}: questões {missing} indisponíveis."
        )
    return questions


def _find_extractor_output(output_dir: Path) -> Path | None:
    candidates = list(output_dir.rglob("*.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _asset_url(path: str) -> str:
    asset_path = Path(path)
    try:
        relative = asset_path.resolve().relative_to(CACHE_DIR.resolve())
    except ValueError:
        return path
    return f"/cache-assets/{relative.as_posix()}"


def _blocks_to_parts(blocks: list[dict]) -> tuple[str, list[str]]:
    text_parts: list[str] = []
    files: list[str] = []

    for block in blocks or []:
        block_type = block.get("type")
        if block_type == "text":
            content = (block.get("content") or "").strip()
            if content:
                text_parts.append(content)
        elif block_type == "image":
            image_path = block.get("content") or ""
            if image_path:
                files.append(_asset_url(image_path))
                text_parts.append(f"![imagem]({_asset_url(image_path)})")

    return " ".join(text_parts).strip(), files


def _split_context_and_intro(full_text: str) -> tuple[str, str]:
    if not full_text:
        return "", ""

    sentences = [part.strip() for part in full_text.split(". ") if part.strip()]
    if len(sentences) <= 1:
        return full_text, ""

    intro = sentences[-1]
    if not intro.endswith("."):
        intro = f"{intro}."
    context = ". ".join(sentences[:-1])
    if context and not context.endswith("."):
        context = f"{context}."
    return context, intro


def _parse_extractor_item(item: dict, year: int, index: int, language: str) -> Question:
    full_text, files = _blocks_to_parts(item.get("content", []))
    context, intro = _split_context_and_intro(full_text)

    alternatives: list[Alternative] = []
    correct_alternative = ""
    alternatives_raw = item.get("alternatives") or {}

    if isinstance(alternatives_raw, dict):
        ordered_keys = sorted(alternatives_raw.keys(), key=lambda key: int(key))
        for key in ordered_keys:
            alt_data = alternatives_raw[key]
            alt_text, _ = _blocks_to_parts(alt_data.get("content", []))
            letter = str(alt_data.get("alternative") or "").upper()
            is_correct = bool(alt_data.get("correct", False))
            if is_correct:
                correct_alternative = letter
            alternatives.append(
                Alternative(
                    letter=letter,
                    text=alt_text,
                    isCorrect=is_correct,
                )
            )

    discipline = "linguagens" if index <= 45 else "ciencias-humanas"
    return Question(
        year=year,
        index=index,
        discipline=discipline,
        language=language if index <= 5 else None,
        context=context,
        alternativesIntroduction=intro,
        alternatives=alternatives,
        correctAlternative=correct_alternative,
        files=files,
        source="inep-pdf",
    )


def _select_extractor_items(raw_items: list[dict], language: str) -> list[dict]:
    first_foreign: list[dict] = []
    second_foreign: list[dict] = []
    remaining: list[dict] = []
    stage = "first_foreign"

    for item in raw_items:
        number = int(item.get("number", 0))
        if number <= 5:
            if stage == "first_foreign":
                first_foreign.append(item)
                if number == 5:
                    stage = "second_foreign"
            elif stage == "second_foreign":
                second_foreign.append(item)
                if number == 5:
                    stage = "remaining"
        elif stage == "remaining":
            remaining.append(item)

    foreign_block = first_foreign if language == "ingles" else second_foreign
    if len(foreign_block) != 5:
        raise ValueError("Não foi possível identificar o bloco de língua estrangeira no PDF.")

    selected = foreign_block + remaining
    if len(selected) != DAY1_QUESTION_COUNT:
        raise ValueError(
            f"Extração incompleta: {len(selected)}/{DAY1_QUESTION_COUNT} questões no PDF."
        )
    return selected


def _load_extractor_json(json_path: Path, year: int, language: str) -> list[Question]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    raw_items = data.get("data") if isinstance(data, dict) else data
    if not isinstance(raw_items, list):
        raise ValueError("Formato JSON do extractor não reconhecido.")

    selected_items = _select_extractor_items(raw_items, language)
    return [
        _parse_extractor_item(item, year, index, language)
        for index, item in enumerate(selected_items, start=1)
    ]


def _extract_from_pdf(prova_path: Path, gabarito_path: Path, output_dir: Path) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "enem",
        "-f",
        str(prova_path),
        "-g",
        str(gabarito_path),
        "-o",
        str(output_dir),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Falha ao extrair PDF do ENEM.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    json_path = _find_extractor_output(output_dir)
    if not json_path:
        raise FileNotFoundError("Extractor não gerou arquivo JSON.")
    return json_path


async def _load_from_pdf(year: int, caderno: str, language: str) -> list[Question]:
    caderno_num = CADERNO_MAP[caderno]
    prova_path, gabarito_path = await download_exam_pdfs(year, caderno_num)
    output_dir = CACHE_DIR / str(year) / f"extract-D1-CD{caderno_num}"
    json_path = _extract_from_pdf(prova_path, gabarito_path, output_dir)
    return _load_extractor_json(json_path, year, language)


def get_available_years() -> tuple[list[int], list[int], list[int]]:
    api_years = list(API_YEARS)
    pdf_years = list(PDF_YEARS)
    all_years = sorted(set(api_years) | set(pdf_years), reverse=True)
    return all_years, api_years, pdf_years


async def load_day1_exam(year: int, caderno: str, language: str) -> list[Question]:
    cache_file = _cache_path(year, caderno, language)
    if cache_file.exists():
        raw = json.loads(cache_file.read_text(encoding="utf-8"))
        return [Question.model_validate(item) for item in raw]

    questions: list[Question] | None = None
    if year in API_YEARS:
        try:
            questions = await _load_from_api(year, language)
        except ValueError:
            questions = await _load_from_pdf(year, caderno, language)
    elif year in PDF_YEARS:
        questions = await _load_from_pdf(year, caderno, language)
    else:
        raise ValueError(f"Ano {year} não suportado.")

    cache_file.write_text(
        json.dumps([q.model_dump() for q in questions], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return questions


async def sync_year(year: int, caderno: str, language: str) -> tuple[list[Question], str]:
    cache_file = _cache_path(year, caderno, language)
    if cache_file.exists():
        cache_file.unlink()

    questions = await load_day1_exam(year, caderno, language)
    source = questions[0].source if questions else "unknown"
    return questions, source
