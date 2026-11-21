from fastapi import APIRouter, Depends, File, UploadFile

from app.infrastructure.vision.ocr_service import ImageTextExtractor
from app.interfaces.exceptions import AppException
from app.interfaces.http.dependencies import get_current_user
from app.interfaces.http.response import success_response

router = APIRouter()


@router.post("/extract-words")
async def extract_words_from_image(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if image.content_type and not image.content_type.startswith("image/"):
        raise AppException(code=40011, message="Please upload an image file", status_code=400)

    image_bytes = await image.read()
    result = ImageTextExtractor().extract(image_bytes)

    return success_response(
        {
            "filename": image.filename,
            "user_id": current_user.get("id"),
            "text": result.text,
            "words": result.words,
            "total_candidates": result.total_candidates,
            "preprocessing": result.preprocessing,
            "engine": result.engine,
        },
        "Words extracted from image",
    )
