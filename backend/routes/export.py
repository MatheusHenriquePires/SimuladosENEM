from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from fpdf.errors import FPDFException

from backend.services.mixer import load_mix
from backend.services.pdf_exporter import export_mixed_exam_pdf

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/mix/{exam_id}/pdf")
async def download_mix_pdf(exam_id: str) -> Response:
    try:
        exam = load_mix(exam_id)
        pdf_bytes = export_mixed_exam_pdf(exam)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FPDFException as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {exc}") from exc

    filename = f"enem-mesclado-{exam_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
