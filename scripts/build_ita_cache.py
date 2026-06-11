# scripts/build_ita_cache.py
import json
import os
import re
from pathlib import Path

# Resolve o caminho a partir da pasta scripts para a raiz
ROOT_DIR = Path(__file__).resolve().parent.parent
ITA_DIR = ROOT_DIR / "ita"
OUTPUT_JSON = ROOT_DIR / "data" / "cache" / "ita_cache.json"

def parse_markdown_question(filepath: Path) -> dict:
    content = filepath.read_text(encoding="utf-8")
    
 # Tenta extrair o gabarito (Ex: Gabarito: A ou Resposta: B)
    correct_alt = None
    gabarito_match = re.search(r'(?i)(gabarito|resposta):\s*([A-E])', content)
    if gabarito_match:
        correct_alt = gabarito_match.group(2).upper()
    return {
        "context": content.strip(),
        "correctAlternative": correct_alt
    }

def build_cache():
    questions = []

    if not ITA_DIR.exists():
        print(f"Erro: A pasta {ITA_DIR} não foi encontrada.")
        print("Faça o download do repositório ita-brain e coloque na pasta correta.")
        return

    subjects = ["fisica", "matematica", "quimica"]
    
    for subject in subjects:
        subject_dir = ITA_DIR / subject
        if not subject_dir.exists():
            continue
            
        for year_dir in subject_dir.iterdir():
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            
            year = int(year_dir.name)
            
            for phase_dir in year_dir.iterdir():
                if not phase_dir.is_dir() or "fase" not in phase_dir.name.lower():
                    continue
                
                phase = 1 if "1" in phase_dir.name else 2
                
                for q_file in phase_dir.glob("Q*.md"):
                    # Extrai o número da questão (ex: Q01.md -> 1)
                    idx_match = re.search(r'\d+', q_file.name)
                    index = int(idx_match.group()) if idx_match else 0
                    
                    parsed = parse_markdown_question(q_file)
                    
                    questions.append({
                        "id": f"ita-{year}-f{phase}-{subject}-q{index}",
                        "year": year,
                        "phase": phase,
                        "subject": subject,
                        "index": index,
                        "context": parsed["context"],
                        "correctAlternative": parsed["correctAlternative"],
                        "source": "ita-brain"
                    })

    # Salva o cache
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cache do ITA gerado com sucesso! {len(questions)} questões processadas.")

if __name__ == "__main__":
    build_cache()