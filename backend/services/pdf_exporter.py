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
    def __init__(self, color_name="AZUL", exam_day="1º DIA"):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=15)
        self.color_name = color_name
        self.exam_day = exam_day
        
        # Define a cor da caixa da capa com base no nome do caderno
        self.rgb_color = (30, 144, 255)  # Azul padrão
        if color_name.upper() == "AMARELO":
            self.rgb_color = (255, 215, 0)
        elif color_name.upper() == "ROSA":
            self.rgb_color = (255, 105, 180)
        elif color_name.upper() == "BRANCO":
            self.rgb_color = (220, 220, 220)
        elif color_name.upper() == "VERDE":
            self.rgb_color = (34, 139, 34)
        elif color_name.upper() == "CINZA":
            self.rgb_color = (128, 128, 128)
            
    def add_cover_page(self):
        self.add_page()
        
        # ---- Cabeçalho da Capa (Logo da Instituição) ----
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(50, 50, 50)
        self.set_y(20)
        self.cell(0, 10, "colégio propósito", align="C", ln=True)
        
        self.set_font("Helvetica", "", 12)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "EXAME NACIONAL DO ENSINO MÉDIO", align="C", ln=True)
        
        self.ln(10)
        
        # ---- Bloco de Cor e Título do Caderno ----
        self.set_fill_color(*self.rgb_color)
        self.rect(20, 50, 170, 30, 'F')
        
        if self.color_name.upper() in ["BRANCO", "AMARELO"]:
            self.set_text_color(0, 0, 0)
        else:
            self.set_text_color(255, 255, 255)
            
        self.set_font("Helvetica", "B", 18)
        self.set_xy(20, 55)
        self.cell(170, 10, "SIMULADO ENEM EXCLUSIVO", align="C", ln=True)
        self.set_font("Helvetica", "B", 14)
        self.set_xy(20, 65)
        self.cell(170, 10, f"CADERNO - {self.color_name.upper()}", align="C", ln=True)
        
        self.set_text_color(0, 0, 0)
        
        # ---- Identificação do Aluno ----
        self.set_y(95)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, "NOME DO ALUNO:", ln=True)
        self.rect(20, 101, 170, 10)
        
        self.set_y(115)
        self.cell(80, 6, "NÚMERO DE INSCRIÇÃO / RA:", ln=True)
        self.rect(20, 121, 80, 10)
        
        self.set_xy(110, 115)
        self.cell(80, 6, "TURMA / UNIDADE:", ln=True)
        self.rect(110, 121, 80, 10)
        
        # ---- Instruções no formato ENEM ----
        self.set_y(145)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "LEIA ATENTAMENTE AS INSTRUÇÕES SEGUINTES:", ln=True)
        
        self.set_font("Helvetica", "", 10)
        instrucoes = [
            "1. Este CADERNO DE QUESTÕES contém as questões sorteadas para o seu simulado.",
            "2. Confira se a quantidade e a ordem das questões do seu caderno estão corretas.",
            "3. O tempo disponível para estas provas deve seguir a recomendação do seu cronograma.",
            "4. Reserve tempo suficiente para preencher o CARTÃO-RESPOSTA ou a plataforma.",
            "5. Os rascunhos e as marcações assinaladas neste caderno não serão considerados na avaliação."
        ]
        
        for inst in instrucoes:
            self.multi_cell(170, 6, inst)
            self.ln(2)

    def header(self):
        # Omitir o cabeçalho na Capa
        if self.page_no() == 1:
            return
            
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(50, 50, 50)
        self.cell(50, 8, "colégio propósito", ln=0)
        
        self.set_font("Helvetica", "I", 10)
        self.cell(0, 8, f"Simulado ENEM - Caderno {self.color_name.capitalize()}", align="R", ln=True)
        
        self.set_draw_color(200, 200, 200)
        self.line(10, 18, 200, 18)
        self.ln(5)

    def footer(self):
        # Omitir o rodapé na Capa
        if self.page_no() == 1:
            return
            
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, f'{self.exam_day} | Página {self.page_no() - 1}', 0, 0, 'C')


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
    day_str = f"{exam.day}º DIA"
    pdf = EnemPDF(color_name=exam.caderno, exam_day=day_str)
    pdf.set_margins(15, 15, 15)
    
    # 1. Adiciona a Capa Padronizada
    pdf.add_cover_page()
    
    # 2. Inicia as páginas de questões
    pdf.add_page()

    # Informações de metadados do gerador
    _write_line(pdf, f"Anos sorteados: {', '.join(str(y) for y in exam.years)}", size=9, style="I")
    if exam.day == 1:
        _write_line(pdf, f"Idioma (Q1-5): {exam.language.capitalize()}", size=9, style="I")
    _write_line(pdf, f"Gerado em: {exam.createdAt[:19]}", size=9, style="I")
    pdf.ln(5)

    # 3. Renderiza as questões
    for question in exam.questions:
        header = (
            f"Questão {question.mixedIndex} "
            f"(ENEM {question.originalYear}, item {question.originalIndex})"
        )
        _write_line(pdf, header, style="B", size=11)

        if question.context:
            _write_markdown_content(pdf, question.context)

        if question.alternativesIntroduction:
            _write_markdown_content(pdf, question.alternativesIntroduction)

        for alt in question.alternatives:
            _write_markdown_content(pdf, f"{alt.letter}) {alt.text}")

        pdf.ln(2)

    # 4. Adiciona o Gabarito Consolidado no final
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