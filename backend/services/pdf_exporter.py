import re
from io import BytesIO
from urllib.parse import unquote

from fpdf import FPDF

from backend.config import CACHE_DIR
from backend.models import MixedExam


def _clean_text_formatting(text: str) -> str:
    """Limpa marcações markdown de links e negrito/itálico, preservando imagens."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.replace("\r\n", "\n").strip()


def _safe_text(text: str) -> str:
    """Garante que o texto seja compatível com a codificação latin-1 padrão do FPDF."""
    if not text:
        return ""
    cleaned = _clean_text_formatting(text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.encode("latin-1", errors="replace").decode("latin-1")


class EnemPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", align="C")


def _resolve_image_path(url_or_path: str) -> str | None:
    """Mapeia a URL pública da imagem de volta para o caminho real no disco."""
    if url_or_path.startswith("http"):
        return url_or_path  # FPDF2 consegue baixar URLs HTTP nativamente se necessário
    
    if url_or_path.startswith("/cache-assets/"):
        rel_path = unquote(url_or_path.replace("/cache-assets/", ""))
        local_path = CACHE_DIR / rel_path
        if local_path.exists():
            return str(local_path)
            
    return None


def _write_line(pdf: FPDF, text: str, height: float = 6, style: str = "", size: int = 10) -> None:
    if not text.strip():
        return
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", style, size)
    pdf.multi_cell(pdf.epw, height, _safe_text(text))


def _write_markdown_content(pdf: FPDF, text: str, height: float = 6, size: int = 10) -> None:
    """Analisa o markdown e intercala blocos de texto com renderização de imagens."""
    if not text:
        return
    
    # Encontra as imagens no padrão: ![alt](url)
    pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    last_end = 0
    
    for match in pattern.finditer(text):
        # 1. Escreve o texto que aparece ANTES da imagem
        text_before = text[last_end:match.start()].strip()
        if text_before:
            _write_line(pdf, text_before, height=height, size=size)
        
        # 2. Prepara e desenha a imagem
        img_url = match.group(1)
        img_path = _resolve_image_path(img_url)
        
        if img_path:
            try:
                # Centraliza a imagem na página usando largura de 70% da margem útil
                w = pdf.epw * 0.7
                x = pdf.l_margin + (pdf.epw * 0.15)
                pdf.image(img_path, x=x, w=w)
                pdf.ln(3)  # Pequena quebra de linha após a imagem
            except Exception as e:
                # Fallback seguro caso o arquivo esteja corrompido ou o FPDF falhe ao ler
                _write_line(pdf, "[Erro ao renderizar imagem]", height=height, size=size)
        else:
            _write_line(pdf, "[Imagem indisponível offline]", height=height, size=size)
            
        last_end = match.end()
        
    # 3. Escreve qualquer texto que tenha sobrado DEPOIS da última imagem
    text_after = text[last_end:].strip()
    if text_after:
        _write_line(pdf, text_after, height=height, size=size)


def export_mixed_exam_pdf(exam: MixedExam) -> bytes:
    pdf = EnemPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    _write_line(pdf, f"ENEM Mesclador - Simulado Dia {exam.day}", style="B", size=16, height=8)
    _write_line(pdf, f"Anos: {', '.join(str(y) for y in exam.years)}", size=11)
    _write_line(pdf, f"Caderno: {exam.caderno.capitalize()}", size=11)
    if exam.day == 1:
        _write_line(pdf, f"Idioma (Q1-5): {exam.language.capitalize()}", size=11)
    _write_line(pdf, f"Gerado em: {exam.createdAt[:19]}", size=11)
    pdf.ln(3)

    for question in exam.questions:
        header = (
            f"Questao {question.mixedIndex} "
            f"(ENEM {question.originalYear}, item {question.originalIndex})"
        )
        _write_line(pdf, header, style="B", size=11)

        # Substitui _write_line padrão pelo nosso novo motor de markdown com imagens
        if question.context:
            _write_markdown_content(pdf, question.context)

        if question.alternativesIntroduction:
            _write_markdown_content(pdf, question.alternativesIntroduction)

        for alt in question.alternatives:
            # Funciona perfeitamente aqui também! Ex: Se a letra A for apenas uma imagem, 
            # ele escreve "A) " na tela e logo abaixo renderiza a imagem.
            _write_markdown_content(pdf, f"{alt.letter}) {alt.text}")

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