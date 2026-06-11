import traceback
from fastapi import APIRouter, HTTPException

from backend.models import ItaMixRequest
from backend.services.ita_mixer import build_ita_mixed_exam

router = APIRouter(prefix="/api/ita", tags=["ita"])

@router.post("/mix")
async def create_ita_mix(request: ItaMixRequest):
    try:
        return await build_ita_mixed_exam(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        # ISSO VAI IMPRIMIR O ERRO REAL NO SEU TERMINAL:
        print("=== ERRO AO GERAR SIMULADO ITA ===")
        traceback.print_exc() 
        print("==================================")
        
        # Devolve o erro para o frontend exibir na tela
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(exc)}")