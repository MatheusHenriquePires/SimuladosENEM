import re
from io import BytesIO

from fpdf import FPDF

from backend.models import MixedExam


def _strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "[imagem]", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.replace("\r\n", "\n").strip()


def _safe_text(text: str) -> str:
    if not text:
        return ""
    cleaned = _strip_markdown(text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.encode("latin-1", errors="replace").decode("latin-1")


class EnemPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")


def _write_line(pdf: FPDF, text: str, height: float = 6, style: str = "", size: int = 10) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", style, size)
    pdf.multi_cell(pdf.epw, height, _safe_text(text))


def export_mixed_exam_pdf(exam: MixedExam) -> bytes:
    pdf = EnemPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    _write_line(pdf, "ENEM Mesclador - Simulado 1o Dia", style="B", size=16, height=8)
    _write_line(pdf, f"Anos: {', '.join(str(y) for y in exam.years)}", size=11)
    _write_line(pdf, f"Caderno: {exam.caderno.capitalize()}", size=11)
    _write_line(pdf, f"Idioma (Q1-5): {exam.language.capitalize()}", size=11)
    _write_line(pdf, f"Gerado em: {exam.createdAt[:19]}", size=11)
    pdf.ln(3)

    for question in exam.questions:
        header = (
            f"Questao {question.mixedIndex} "
            f"(ENEM {question.originalYear}, item {question.originalIndex})"
        )
        _write_line(pdf, header, style="B", size=11)

        if question.context:
            _write_line(pdf, question.context)

        if question.alternativesIntroduction:
            _write_line(pdf, question.alternativesIntroduction)

        for alt in question.alternatives:
            _write_line(pdf, f"{alt.letter}) {alt.text}")

        pdf.ln(2)

    pdf.add_page()
    _write_line(pdf, "Gabarito Consolidado", style="B", size=14, height=8)

    columns = 3
    col_width = pdf.epw / columns
    rows_per_col = 30
    start_y = pdf.get_y()

    for col in range(columns):
        pdf.set_xy(pdf.l_margin + col * col_width, start_y)
        start = col * rows_per_col
        end = min(start + rows_per_col, len(exam.questions))
        for question in exam.questions[start:end]:
            line = (
                f"Q{question.mixedIndex:02d}: {question.correctAlternative} "
                f"({question.originalYear})"
            )
            pdf.multi_cell(col_width, 5, _safe_text(line))

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
