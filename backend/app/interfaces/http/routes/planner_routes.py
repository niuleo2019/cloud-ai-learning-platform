from fastapi import APIRouter, Depends, Query

from app.application.schemas import PracticeAttemptRequest, StudyPlanDoneRequest, StudyPlanRequest
from app.infrastructure.repositories.mysql_listening_repository import MySQLListeningRepository
from app.infrastructure.repositories.mysql_planner_repository import MySQLPracticeRepository, MySQLStudyPlanRepository
from app.interfaces.exceptions import AppException
from app.interfaces.http.dependencies import build_planner_service, get_current_user
from app.interfaces.http.response import success_response

router = APIRouter()


@router.post("/attempts")
def record_attempt(payload: PracticeAttemptRequest, current_user: dict = Depends(get_current_user)):
    """Store one dictation / retell result; the planner reads these to find weaknesses."""
    if not MySQLListeningRepository().find_by_id_and_user(payload.material_id, current_user["id"]):
        raise AppException(40420, "Listening material not found", 404)
    MySQLPracticeRepository().record(current_user["id"], payload.model_dump())
    return success_response({"recorded": True}, "Practice attempt recorded")


@router.get("/today")
def get_plan(date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"), current_user: dict = Depends(get_current_user)):
    """The saved plan for the learner's local date (the phone sends it), or empty when there is none."""
    return success_response(MySQLStudyPlanRepository().find(current_user["id"], date), "Study plan")


@router.post("/plan")
def make_plan(payload: StudyPlanRequest, current_user: dict = Depends(get_current_user)):
    """Run the study-planning agent (30-90 s) and save today's plan."""
    service = build_planner_service(current_user["id"], payload.date)
    return success_response(service.make_plan(payload.minutes, payload.focus), "Study plan created")


@router.put("/today/done")
def set_done(payload: StudyPlanDoneRequest, current_user: dict = Depends(get_current_user)):
    plan = MySQLStudyPlanRepository().set_done(current_user["id"], payload.date, payload.done)
    if plan is None:
        raise AppException(40450, "No plan for this day", 404)
    return success_response(plan, "Plan progress saved")
