import json
import re
from pathlib import Path
from pypdf import PdfReader
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import argparse

# Adiciona suporte a OCR (fallback) usando pytesseract + pdf2image
OCR_AVAILABLE = False
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

SITE_PROVAS_URL = "https://www.vestibular.ita.br/provas.htm"


def ocr_page(pdf_path: Path, page_number: int) -> str:
    """Converte uma página do PDF em imagem e roda OCR para extrair texto."""
    try:
        images = convert_from_path(str(pdf_path), first_page=page_number + 1, last_page=page_number + 1)
        if not images:
            return ""
        img = images[0]
        text = pytesseract.image_to_string(img, lang='por+eng')
        return text
    except Exception:
        return ""


def extract_questions_from_pdf(pdf_path: Path, materia: str, ano: int, fase: int):
    print(f"📖 Lendo o arquivo PDF: {pdf_path.name}...")
    reader = PdfReader(pdf_path)
    
    # 1. Extrai todo o texto do PDF unificado, com fallback por OCR quando a extração direta falhar
    full_text = ""
    for page_index, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and len(text.strip()) > 50:
            full_text += text + "\n"
        else:
            if OCR_AVAILABLE:
                ocr_text = ocr_page(pdf_path, page_index)
                if ocr_text and len(ocr_text.strip()) > 10:
                    print(f"🔎 Texto via OCR extraído da página {page_index + 1}")
                    full_text += ocr_text + "\n"
                else:
                    # tenta adicionar qualquer texto bruto mesmo pequeno
                    if text:
                        full_text += (text + "\n")
            else:
                if text:
                    full_text += (text + "\n")

    # 2. Regex para capturar os blocos de cada questão (ex: "Questão 01.")
    pattern = re.compile(r'(Questão\s+\d+[\s\S]+?)(?=Questão\s+\d+|\Z)', re.IGNORECASE)
    matches = pattern.findall(full_text)

    questions = []
    for index, block in enumerate(matches, start=1):
        block_cleaned = block.strip()
        
        # Tenta capturar o número real da questão no PDF
        num_match = re.search(r'Questão\s+(\d+)', block_cleaned, re.IGNORECASE)
        numero_questao = int(num_match.group(1)) if num_match else index

        # Extrai alternativas A-E quando existirem
        # Captura blocos que começam com A), A. ou A - e pega até o próximo rótulo ou fim
        opts = re.findall(r'(?ms)^[\s]*([A-E])[\)\.\-]\s*(.+?)(?=(?:^[\s]*[A-E][\)\.\-])|\Z)', block_cleaned, re.MULTILINE)
        options = []
        if opts:
            for label, text in opts:
                options.append({"label": label.strip(), "text": text.strip()})

        # Monta o ID único no mesmo padrão que já usamos
        quest_id = f"{materia[:3].lower()}-{ano}-f{fase}-q{str(numero_questao).zfill(2)}"

        question_data = {
            "id": quest_id,
            "materia": materia.lower(),
            "ano": ano,
            "fase": fase,
            "numero": numero_questao,
            "context": block_cleaned,
            "correctAlternative": None,
            "options": options,
            "tipo": "multipla_escolha" if options else "dissertativa",
            "source": "pdf-extractor"
        }
        questions.append(question_data)

    print(f"✅ Sucesso! {len(questions)} questões extraídas.")
    return questions


def show_questions(questions):
    """Imprime as questões extraídas com suas alternativas (se houver)."""
    for q in questions:
        print("----------------------------------------")
        print(f"ID: {q['id']}  —  Q{q['numero']}")
        # Mostra apenas as primeiras linhas do contexto para não poluir demais
        ctx_preview = "\n".join(q['context'].splitlines()[:6])
        print(ctx_preview)
        if q.get('options'):
            for opt in q['options']:
                print(f"  {opt['label']}) {opt['text']}")
        else:
            print("  (sem alternativas detectadas)")
    print("----------------------------------------")


def get_pdf_links_from_page(url: str):
    """Retorna lista de URLs de PDFs encontrados na página fornecida."""
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf'):
                full = urljoin(url, href)
                links.append(full)
        return links
    except Exception as e:
        print(f"⚠️ Erro ao buscar links de PDF: {e}")
        return []


def download_pdfs(links, dest_dir: Path, max_files: int = 10):
    """Baixa os PDFs fornecidos para dest_dir. Retorna lista de caminhos salvos."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for idx, link in enumerate(links):
        if idx >= max_files:
            break
        try:
            fname = link.split('/')[-1].split('?')[0]
            out_path = dest_dir / fname
            if out_path.exists():
                saved.append(out_path)
                continue
            print(f"⬇️ Baixando: {fname}")
            r = requests.get(link, stream=True, timeout=30)
            r.raise_for_status()
            with open(out_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            saved.append(out_path)
        except Exception as e:
            print(f"⚠️ Falha ao baixar {link}: {e}")
    return saved


def run_ingestion(pdf_path: Path | None = None, materia: str = "matematica", ano: int = 2008, fase: int = 1, max_download: int = 8, force_no_ocr: bool = False):
    # Caminhos das pastas
    ROOT_DIR = Path(__file__).resolve().parent.parent

    # Respeita flag de desabilitar OCR
    use_ocr = OCR_AVAILABLE and (not force_no_ocr)

    # Coloque os seus PDFs baixados dentro de uma pasta (ex: ita-brain/_inbox/)
    INBOX_DIR = ROOT_DIR / "ita-brain" / "_inbox"
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON = ROOT_DIR / "ita-brain" / "banco_questoes_local.json"

    # Se um caminho de PDF foi passado explicitamente, usa ele
    if pdf_path:
        chosen_pdf = Path(pdf_path)
        if not chosen_pdf.exists():
            print(f"❌ PDF especificado não encontrado: {chosen_pdf}")
            return
    else:
        # Se não houver PDFs no _inbox, tenta baixar do site do ITA
        local_pdfs = list(INBOX_DIR.glob('*.pdf'))
        if not local_pdfs:
            print("🧭 _inbox vazio — tentando baixar PDFs do site do ITA...")
            links = get_pdf_links_from_page(SITE_PROVAS_URL)
            if links:
                downloaded = download_pdfs(links, INBOX_DIR, max_files=max_download)
                local_pdfs = downloaded
            else:
                print("❌ Não foram encontrados links de PDF no site.")

        if not local_pdfs:
            print(f"❌ Erro: Nenhum PDF disponível em: {INBOX_DIR}")
            print("Coloque manualmente o arquivo PDF em: " + str(INBOX_DIR))
            return

        # Tenta selecionar um PDF com base no nome da matéria, senão pega o primeiro
        chosen_pdf = None
        for p in local_pdfs:
            if materia and materia.lower() in p.name.lower():
                chosen_pdf = p
                break
        if not chosen_pdf:
            chosen_pdf = local_pdfs[0]

    print(f"➡️ Processando PDF selecionado: {chosen_pdf.name}")

    # Executa a extração com opção de OCR conforme detectado/forçado
    # Passa parâmetro materia/ano/fase para construir IDs corretamente
    extracted = extract_questions_from_pdf(chosen_pdf, materia=materia, ano=ano, fase=fase)

    # Carrega banco existente para não apagar dados antigos se rodar com múltiplos PDFs
    existing_data = []
    if OUTPUT_JSON.exists():
        try:
            existing_data = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
        except:
            existing_data = []

    # Evita duplicados combinando pelo ID da questão
    existing_ids = {q["id"] for q in existing_data}
    for q in extracted:
        if q["id"] not in existing_ids:
            existing_data.append(q)

    # Salva o arquivo JSON estruturado completo
    OUTPUT_JSON.write_text(json.dumps(existing_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"💾 Banco de dados local atualizado em: {OUTPUT_JSON}")

    # Mostra as questões extraídas no terminal para verificação rápida
    show_questions(extracted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrai questões de PDFs do site do ITA e salva em JSON local.")
    parser.add_argument('--pdf', help='Caminho para um arquivo PDF local específico a processar')
    parser.add_argument('--materia', default='matematica', help='Nome da matéria para construir IDs e filtrar PDFs')
    parser.add_argument('--ano', type=int, default=2008, help='Ano da prova (usado no id)')
    parser.add_argument('--fase', type=int, default=1, help='Fase da prova (usado no id)')
    parser.add_argument('--max-download', type=int, default=8, help='Máximo de PDFs a baixar quando popular o _inbox')
    parser.add_argument('--no-ocr', action='store_true', help='Desabilita o uso de OCR mesmo que esteja disponível')
    parser.add_argument('--list', action='store_true', help='Lista PDFs presentes em ita-brain/_inbox e sai')
    args = parser.parse_args()

    # Se listar PDFs e sair
    if args.list:
        INBOX_DIR = Path(__file__).resolve().parent.parent / "ita-brain" / "_inbox"
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        pdfs = list(INBOX_DIR.glob('*.pdf'))
        if not pdfs:
            print("Nenhum PDF encontrado em _inbox.")
        else:
            print("PDFs em _inbox:")
            for p in pdfs:
                print(" - " + str(p.name))
        raise SystemExit(0)

    run_ingestion(pdf_path=Path(args.pdf) if args.pdf else None, materia=args.materia, ano=args.ano, fase=args.fase, max_download=args.max_download, force_no_ocr=args.no_ocr)