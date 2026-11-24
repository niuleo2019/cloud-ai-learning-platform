from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

from app.application.schemas import DictionaryOrderRequest, DictionaryUpdateRequest
from app.application.services.dictionary_library_service import DictionaryLibraryService
from app.interfaces.http.dependencies import get_current_user, get_dictionary_library_service
from app.interfaces.http.response import success_response

router = APIRouter()


@router.get("")
def list_dictionaries(
    _current_user: dict = Depends(get_current_user),
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    return success_response(service.list_dictionaries(), "Dictionaries")


@router.post("")
async def import_dictionary(
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    uploads = [(item.filename or "", item.file) for item in files]
    # Copying a large .mdd and reading the .mdx index is blocking work: keep it off the event loop.
    created = await run_in_threadpool(service.import_files, current_user["id"], uploads)
    return success_response(created, "Dictionary imported")


@router.post("/scan")
def scan_dictionaries(
    current_user: dict = Depends(get_current_user),
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    return success_response(service.scan(current_user["id"]), "Dictionary folder scanned")


@router.put("/order")
def reorder_dictionaries(
    payload: DictionaryOrderRequest,
    _current_user: dict = Depends(get_current_user),
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    return success_response(service.reorder(payload.ids), "Dictionary order saved")


@router.get("/lookup")
def lookup_word(
    word: str = Query(min_length=1, max_length=120),
    _current_user: dict = Depends(get_current_user),
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    return success_response(service.lookup(word), "Dictionary entries")


@router.get("/examples")
def example_sentences(
    word: str = Query(min_length=1, max_length=120),
    _current_user: dict = Depends(get_current_user),
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    """Example sentences with real recordings (e.g. LDOCE), played through the signed resource URL."""
    return success_response(service.examples(word), "Example sentences with audio")


@router.get("/suggest")
def suggest_words(
    prefix: str = Query(min_length=1, max_length=120),
    _current_user: dict = Depends(get_current_user),
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    return success_response(service.suggest(prefix), "Suggestions")


@router.patch("/{dictionary_id}")
def update_dictionary(
    dictionary_id: int,
    payload: DictionaryUpdateRequest,
    _current_user: dict = Depends(get_current_user),
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    return success_response(service.update(dictionary_id, payload.title, payload.enabled), "Dictionary updated")


@router.delete("/{dictionary_id}")
def delete_dictionary(
    dictionary_id: int,
    _current_user: dict = Depends(get_current_user),
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    return success_response(service.delete(dictionary_id), "Dictionary deleted")


@router.get("/{dictionary_id}/res/{token}/{path:path}")
def dictionary_resource(
    dictionary_id: int,
    token: str,
    path: str,
    service: DictionaryLibraryService = Depends(get_dictionary_library_service),
):
    """CSS, images, fonts and audio referenced by an entry. Authorised by the signed token in the URL."""
    data, content_type = service.resource(dictionary_id, token, path)
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, max-age=86400"})
