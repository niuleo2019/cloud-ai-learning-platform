from fastapi import APIRouter, Depends, Query

from app.application.services.word_explainer_service import WordExplainerService
from app.interfaces.http.dependencies import get_current_user, get_word_explainer_service
from app.interfaces.http.response import success_response

router = APIRouter()


@router.get("/{word}")
def get_explanation(
    word: str,
    _current_user: dict = Depends(get_current_user),
    service: WordExplainerService = Depends(get_word_explainer_service),
):
    """The cached explanation, or null when the word has not been explained yet (no AI call)."""
    return success_response(service.get_cached(word), "Word explanation")


@router.post("/{word}")
def generate_explanation(
    word: str,
    regenerate: bool = Query(default=False),
    current_user: dict = Depends(get_current_user),
    service: WordExplainerService = Depends(get_word_explainer_service),
):
    """Generate with Claude (30-90 s) unless already cached; `regenerate=true` replaces the cached one."""
    return success_response(service.generate(word, current_user["id"], regenerate), "Word explanation generated")
