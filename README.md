# ENEM Mesclador

Ferramenta para gerar simulados do **1º dia do ENEM** mesclando questões de diferentes anos, com alternância por questão (Q1=2024, Q2=2023, Q3=2022, Q4=2024...).

## Funcionalidades

- Download de provas e gabaritos oficiais do [INEP](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos)
- Questões de 2009–2023 via [API enem.dev](https://enem.dev)
- Questões de 2024+ via extração de PDF (`enem` extractor)
- Interface web para gerar e estudar simulados
- Exportação em PDF com gabarito consolidado

## Requisitos

- Python 3.11+

## Instalação

```bash
cd c:\Users\OBJETIVO\Documents\Matheus\1
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Executar

```bash
uvicorn backend.main:app --reload
```

Acesse: http://localhost:8000

## API

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/years` | Lista anos disponíveis |
| `POST /api/mix` | Gera simulado mesclado |
| `POST /api/sync/{year}` | Força recarga de um ano |
| `GET /api/mix/{id}/pdf` | Baixa PDF do simulado |

### Exemplo

```bash
curl -X POST http://localhost:8000/api/mix \
  -H "Content-Type: application/json" \
  -d "{\"years\":[2024,2023,2022],\"caderno\":\"azul\",\"language\":\"ingles\"}"
```

## Estrutura

```
backend/          # FastAPI + serviços
frontend/         # Interface web
data/cache/       # Cache de questões (gerado automaticamente)
data/pdfs/        # PDFs baixados do INEP
data/mixes/       # Simulados gerados
```
