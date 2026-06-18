# app/products/router/tkp_generation.py

from io import BytesIO
from fastapi import APIRouter
from docxtpl import DocxTemplate
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/tkp_generation", tags=["TKP"])


# === TKP Generation Endpoints ===

@router.post("/")
async def tkp_generation(
        user_dict: dict
):
    doc = DocxTemplate("templates/tkp_template.docx")

    doc.render(user_dict)

    result_stream = BytesIO()
    doc.save(result_stream)
    result_stream.seek(0)

    return StreamingResponse(
        result_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": 'attachment; filename="generated_tkp.docx"'
        }
    )
