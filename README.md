# ENEM Mesclador

Ferramenta para gerar simulados do ENEM mesclando questoes de diferentes anos.

## Funcionalidades

- Geracao aleatoria de simulado por aluno, sorteando anos e caderno a cada nova prova
- Opcao de simulado do Dia 1 ou Dia 2
- Marcacao das alternativas no navegador, com respostas salvas por simulado
- Download de provas e gabaritos oficiais do INEP
- Questoes de 2009-2023 via API enem.dev
- Questoes de 2024+ via extracao de PDF (`enem` extractor)
- Interface web para gerar e estudar simulados
- Exportacao em PDF com gabarito consolidado

## Requisitos

- Python 3.11+

## Instalacao

```bash
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

| Endpoint | Descricao |
|----------|-----------|
| `GET /api/years` | Lista anos disponiveis |
| `POST /api/mix` | Gera simulado mesclado com dia escolhido, anos e caderno sorteados |
| `POST /api/sync/{year}` | Forca recarga de um ano |
| `GET /api/mix/{id}/pdf` | Baixa PDF do simulado |

### Exemplo

```bash
curl -X POST http://localhost:8000/api/mix \
  -H "Content-Type: application/json" \
  -d "{\"day\":1,\"language\":\"ingles\",\"studentId\":\"aluno-demo\"}"
```

## Estrutura

```text
backend/          # FastAPI + servicos
frontend/         # Interface web
data/cache/       # Cache de questoes (gerado automaticamente)
data/pdfs/        # PDFs baixados do INEP
data/mixes/       # Simulados gerados
```
