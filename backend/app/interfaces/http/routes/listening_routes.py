from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.application.schemas import SentenceUpdateRequest
from app.application.services.listening_service import ListeningService
from app.interfaces.http.dependencies import get_current_user, get_listening_service
from app.interfaces.http.response import success_response

router = APIRouter()


@router.post("/materials")
async def upload_material(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    title: str = Form(default="", max_length=200),
    current_user: dict = Depends(get_current_user),
    service: ListeningService = Depends(get_listening_service),
):
    data = await audio.read()
    material = service.create_material(current_user["id"], title, audio.filename or "audio", data)
    # Transcription takes from seconds to a few minutes; the page polls the status.
    background_tasks.add_task(service.process_material, material["id"], material["audio_file"])
    material.pop("audio_file", None)
    return success_response(material, "Audio uploaded, transcribing")


@router.get("/materials")
def list_materials(
    current_user: dict = Depends(get_current_user),
    service: ListeningService = Depends(get_listening_service),
):
    return success_response(service.list_materials(current_user["id"]), "Listening materials")


@router.get("/materials/{material_id}")
def get_material(
    material_id: int,
    current_user: dict = Depends(get_current_user),
    service: ListeningService = Depends(get_listening_service),
):
    material = service.get_material(current_user["id"], material_id)
    material.pop("audio_file", None)
    material.pop("user_id", None)
    return success_response(material, "Listening material")


@router.get("/materials/{material_id}/audio")
def get_material_audio(
    material_id: int,
    current_user: dict = Depends(get_current_user),
    service: ListeningService = Depends(get_listening_service),
):
    return FileResponse(service.get_audio_path(current_user["id"], material_id))


@router.put("/materials/{material_id}/sentences/{index}")
def update_sentence(
    material_id: int,
    index: int,
    payload: SentenceUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: ListeningService = Depends(get_listening_service),
):
    sentence = service.update_sentence_text(current_user["id"], material_id, index, payload.text)
    return success_response(sentence, "Sentence updated")


@router.delete("/materials/{material_id}")
def delete_material(
    material_id: int,
    current_user: dict = Depends(get_current_user),
    service: ListeningService = Depends(get_listening_service),
):
    return success_response(service.delete_material(current_user["id"], material_id), "Listening material deleted")


@router.post("/retell")
async def recognise_retell(
    audio: UploadFile = File(...),
    _current_user: dict = Depends(get_current_user),
    service: ListeningService = Depends(get_listening_service),
):
    return success_response(service.recognise_retell(await audio.read()), "Retell recognised")
