from fastapi import APIRouter, Query

from app.infrastructure.dictionary.longman_dictionary import lookup_longman_word
from app.interfaces.http.response import success_response

router = APIRouter()


@router.get("/lookup")
def lookup_dictionary(word: str = Query(min_length=1, max_length=120)):
    result = lookup_longman_word(word)
    return success_response(result, "Dictionary lookup")
