import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image

# Tenta importar a biblioteca do cliente (genai). Se não funcionar, continuará com OCR local se disponível.
try:
    from google import genai
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

# Segurança: não enviaremos imagens ao serviço externo. Força desabilitar chamadas que incluam imagens.
GENAI_AVAILABLE = False

# Tenta importar pytesseract para fallback local
try:
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# Carrega a chave da API do .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Se a API não estiver disponível ou chave ausente, seguimos com OCR local (se instalado)
if GENAI_AVAILABLE and not API_KEY:
    print("AVISO: GEMINI_API_KEY não encontrada no arquivo .env — usaremos OCR local quando possível.")

if GENAI_AVAILABLE and API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"AVISO: falha ao inicializar cliente GenAI: {e}. Iremos usar OCR local se disponível.")
        GENAI_AVAILABLE = False

ROOT_DIR = Path(__file__).resolve().parent.parent
ITA_DIR = ROOT_DIR / "ita-brain"
INPUT_JSONL = ITA_DIR / "banco_questoes.json"
OUTPUT_JSONL = ITA_DIR / "banco_questoes_transcrito.json"

PROMPT = """
Transcreva a questão presente nesta imagem para formato texto (Markdown).
Regras estritas:
1. Onde houver equações, números complexos, unidades de medida (ex: m/s²) ou fórmulas matemáticas/físicas/químicas, utilize rigorosamente a sintaxe LaTeX (envolva as fórmulas in-line com $ e blocos separados com $$).
2. NÃO resolva a questão. Apenas transcreva o texto exatamente como aparece.
3. Transcreva as alternativas (se houver) no final do texto.
4. Não adicione comentários como "Aqui está a transcrição", retorne APENAS o texto da questão.
"""


def local_ocr(image: Image.Image) -> str:
    """Faz OCR local com pytesseract se disponível."""
    if not OCR_AVAILABLE:
        return ""
    try:
        # Garante modo RGB
        img = image.convert("RGB")
        text = pytesseract.image_to_string(img, lang='por+eng')
        return text.strip()
    except Exception as e:
        print(f"Erro no OCR local: {e}")
        return ""

def process_ita_database():
    if not INPUT_JSONL.exists():
        print(f"Erro: Arquivo {INPUT_JSONL} não encontrado.")
        return

    # Lê as questões existentes
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    # Verifica quais questões já foram transcritas
    processed_ids = set()
    if OUTPUT_JSONL.exists():
        with open(OUTPUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    processed_ids.add(json.loads(line)["id"])

    print(f"Total de questões: {len(questions)}")
    print(f"Já transcritas: {len(processed_ids)}")

    # Abre o arquivo para continuar adicionando (append)
    with open(OUTPUT_JSONL, "a", encoding="utf-8") as out_file:
        for i, q in enumerate(questions):
            if q["id"] in processed_ids:
                continue
            
            img_path = ITA_DIR / q["imagem"]
            if not img_path.exists():
                print(f"Aviso: Imagem não encontrada para {q['id']} - {img_path}")
                continue

            print(f"[{i+1}/{len(questions)}] A transcrever {q['id']}...")
            
            try:
                # Carrega a imagem
                img = Image.open(img_path)

                transcribed_text = ""
                used_backend = None

                # Primeiro tenta usar a API Gemini quando disponível
                if GENAI_AVAILABLE and API_KEY:
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash-lite',
                            contents=[PROMPT, img]
                        )
                        transcribed_text = response.text.strip()
                        used_backend = 'gemini-2.5-flash-lite'
                    except Exception as e:
                        # Trata 403 / PERMISSION_DENIED de forma explícita e tenta fallback
                        msg = str(e)
                        print(f"Falha na API Gemini: {msg}")
                        if '403' in msg or 'PERMISSION_DENIED' in msg or 'denied' in msg.lower():
                            print("Acesso à API negado (403) — usando OCR local como fallback se possível.")
                        else:
                            print("Erro na chamada à API Gemini — tentando OCR local como fallback.")
                        # segue para fallback

                # Se não usou Gemini (ou falhou), tenta OCR local
                if not transcribed_text:
                    if OCR_AVAILABLE:
                        transcribed_text = local_ocr(img)
                        used_backend = 'local-pytesseract' if transcribed_text else None
                    else:
                        print("OCR local não disponível (pytesseract não instalado). Não foi possível transcrever esta imagem.")

                if not transcribed_text:
                    raise RuntimeError("Nenhuma transcrição obtida (API falhou e OCR local indisponível ou falhou).")

                # Atualiza o JSON
                q["context"] = transcribed_text
                q["transcrito_por"] = used_backend or "unknown"

                # Guarda no novo ficheiro
                out_file.write(json.dumps(q, ensure_ascii=False) + "\n")
                out_file.flush()

                # Pausa para evitar atingir limites
                time.sleep(2)
                
            except Exception as e:
                print(f"Erro ao processar {q['id']}: {e}")
                print("A aguardar 10 segundos antes de tentar a próxima...")
                time.sleep(10)

if __name__ == "__main__":
    process_ita_database()