from fastapi import APIRouter, Depends

from app.application.schemas import AgentChatRequest
from app.application.services.agent_service import AgentService
from app.interfaces.http.dependencies import get_agent_service
from app.interfaces.http.response import success_response

router = APIRouter()


@router.post("/chat")
def chat_with_agent(
    payload: AgentChatRequest,
    agent_service: AgentService = Depends(get_agent_service),
):
    result = agent_service.chat(payload.message, [turn.model_dump() for turn in payload.history])
    return success_response(result, "Agent reply")
