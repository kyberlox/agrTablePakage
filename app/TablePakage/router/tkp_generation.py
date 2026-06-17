# app/products/router/tkp_generation.py
import json
import os
import tempfile
from io import BytesIO

from fastapi import APIRouter, File, Form
from fastapi import UploadFile

from docxtpl import DocxTemplate
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/tkp_generation", tags=["TKP"])


# === TKP Generation Endpoints ===

@router.post("/tkp_generation", description="Генерация ТКП")
async def tkp_generation(
        user_dict: str = Form(...),
        file: UploadFile = File(...),
):
    user_dict = json.loads(user_dict)

    template_bytes = await file.read()

    template_stream = BytesIO(template_bytes)
    doc = DocxTemplate(template_stream)

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
