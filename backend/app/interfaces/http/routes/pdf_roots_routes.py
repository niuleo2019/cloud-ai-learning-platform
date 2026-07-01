from fastapi import APIRouter, Depends, Query

from app.infrastructure.pdf.pdf_roots_service import find_word_in_pdfs, is_available
from app.interfaces.http.dependencies import get_current_user
from app.interfaces.http.response import success_response

router = APIRouter()


@router.get("/search")
def search_pdf_roots(
    word: str = Query(min_length=1, max_length=120),
    _current_user: dict = Depends(get_current_user),
):
    if not is_available():
        return success_response(
            {"available": False, "pages": []},
            "PyMuPDF not installed",
        )

    pages = find_word_in_pdfs(word.strip())
    return success_response(
        {"available": True, "pages": pages},
        "PDF roots search",
    )
