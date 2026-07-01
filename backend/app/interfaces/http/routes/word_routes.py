from fastapi import APIRouter, Depends

from app.application.schemas import WordRequest
from app.application.services.word_service import WordService
from app.interfaces.http.dependencies import get_current_user, get_word_service
from app.interfaces.http.response import success_response

router = APIRouter()


@router.get("")
def list_words(
    current_user: dict = Depends(get_current_user),
    word_service: WordService = Depends(get_word_service),
):
    words = word_service.list_words(current_user["id"])
    return success_response(words, "Word list")


@router.post("")
def create_word(
    payload: WordRequest,
    current_user: dict = Depends(get_current_user),
    word_service: WordService = Depends(get_word_service),
):
    word = word_service.create_word(current_user["id"], payload.model_dump())
    return success_response(word, "Word created")


@router.put("/{word_id}")
def update_word(
    word_id: int,
    payload: WordRequest,
    current_user: dict = Depends(get_current_user),
    word_service: WordService = Depends(get_word_service),
):
    word = word_service.update_word(current_user["id"], word_id, payload.model_dump())
    return success_response(word, "Word updated")


@router.delete("/{word_id}")
def delete_word(
    word_id: int,
    current_user: dict = Depends(get_current_user),
    word_service: WordService = Depends(get_word_service),
):
    result = word_service.delete_word(current_user["id"], word_id)
    return success_response(result, "Word deleted")
