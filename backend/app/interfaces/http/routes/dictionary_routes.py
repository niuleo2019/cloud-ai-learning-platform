from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.infrastructure.dictionary import longman_audio
from app.infrastructure.dictionary.longman_dictionary import lookup_longman_word
from app.infrastructure.speech import piper_tts
from app.interfaces.exceptions import AppException
from app.interfaces.http.response import success_response

router = APIRouter()


@router.get("/lookup")
def lookup_dictionary(word: str = Query(min_length=1, max_length=120)):
    result = lookup_longman_word(word)
    return success_response(result, "Dictionary lookup")


@router.get("/audio")
def word_pronunciation(
    word: str = Query(min_length=1, max_length=60),
    accent: str = Query(default="gb", pattern="^(gb|us)$"),
):
    """Longman pronunciation as WAV. Public (no user data) so <audio src> can load it directly."""
    audio = longman_audio.get_word_audio_wav(word.strip().lower(), accent)
    if audio is None:
        raise AppException(code=40430, message="No Longman pronunciation for this word", status_code=404)
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "public, max-age=604800"})


@router.get("/speak")
def speak_sentence(text: str = Query(min_length=1, max_length=300)):
    """A sentence read by the Piper neural voice (WAV). Public like /audio so <audio src> can load it."""
    clean = " ".join(text.split())
    audio = piper_tts.synthesize_wav(clean)
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "public, max-age=604800"})
