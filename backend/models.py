from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Alternative(BaseModel):
    letter: str
    text: str
    isCorrect: bool = False
    file: str | None = None


class Question(BaseModel):
    year: int
    index: int
    discipline: str
    language: str | None = None
    context: str = ""
    alternativesIntroduction: str = ""
    alternatives: list[Alternative] = Field(default_factory=list)
    correctAlternative: str
    files: list[str] = Field(default_factory=list)
    source: Literal["enem-api", "inep-pdf"] = "enem-api"


class MixedQuestion(Question):
    mixedIndex: int
    originalYear: int
    originalIndex: int


class MixRequest(BaseModel):
    years: list[int] = Field(default_factory=list)
    caderno: Literal["azul", "amarelo", "branco", "verde"] | None = None
    language: Literal["ingles", "espanhol"] = "ingles"
    day: Literal[1, 2] = 1
    studentId: str | None = None

    @field_validator("years")
    @classmethod
    def sort_years_desc(cls, value: list[int]) -> list[int]:
        return sorted(set(value), reverse=True)


class MixedExam(BaseModel):
    id: str
    years: list[int]
    caderno: str
    language: str
    day: int = 1
    questions: list[MixedQuestion]
    createdAt: str


class YearsResponse(BaseModel):
    years: list[int]
    apiYears: list[int]
    pdfYears: list[int]


class SyncResponse(BaseModel):
    year: int
    caderno: str
    language: str
    questionCount: int
    source: str
