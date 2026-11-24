from fastapi import Depends, Header

from app.application.services.agent_service import AgentService, AgentTools
from app.application.services.auth_service import AuthService
from app.application.services.dictionary_library_service import DictionaryLibraryService
from app.application.services.listening_service import ListeningService
from app.application.services.review_service import ReviewService
from app.application.services.planner_service import PlannerService, PlannerTools
from app.application.services.word_explainer_service import WordExplainerService
from app.application.services.word_service import WordService
from app.domain.services.review_policy import ReviewPolicy
from app.infrastructure.config.settings import settings
from app.infrastructure.dictionary.dictionary_files import DictionaryFiles
from app.infrastructure.dictionary.longman_dictionary import lookup_longman_word
from app.infrastructure.dictionary.online_dictionary import lookup_online_word
from app.infrastructure.llm.claude_client import ClaudeClient
from app.infrastructure.repositories.mysql_dictionary_repository import MySQLDictionaryRepository
from app.infrastructure.repositories.mysql_explanation_repository import MySQLExplanationRepository
from app.infrastructure.repositories.mysql_planner_repository import MySQLPracticeRepository, MySQLStudyPlanRepository
from app.infrastructure.repositories.mysql_listening_repository import MySQLListeningRepository
from app.infrastructure.repositories.mysql_review_repository import MySQLReviewRepository
from app.infrastructure.repositories.mysql_user_repository import MySQLUserRepository
from app.infrastructure.repositories.mysql_word_repository import MySQLWordRepository
from app.infrastructure.speech import whisper_transcriber
from app.infrastructure.security.jwt_service import JwtService
from app.infrastructure.security.password_hasher import PasswordHasher
from app.interfaces.exceptions import AppException


def get_auth_service() -> AuthService:
    return AuthService(MySQLUserRepository(), PasswordHasher(), JwtService())


def get_word_service() -> WordService:
    return WordService(MySQLWordRepository())


def get_review_service() -> ReviewService:
    return ReviewService(MySQLReviewRepository(), ReviewPolicy())


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppException(code=40102, message="Missing token", status_code=401)

    token = authorization.replace("Bearer ", "", 1)

    try:
        return JwtService().verify_token(token)
    except ValueError as error:
        raise AppException(code=40103, message=str(error), status_code=401) from error


def lookup_word_offline_first(word: str) -> dict:
    result = lookup_longman_word(word)
    if result.get("found"):
        return {"found": True, "word": result["word"], "definition": result["text"], "source": result["source"]}
    return lookup_online_word(word)


def get_agent_service(current_user: dict = Depends(get_current_user)) -> AgentService:
    tools = AgentTools(
        user_id=current_user["id"],
        word_service=get_word_service(),
        review_service=get_review_service(),
        lookup_word=lookup_word_offline_first,
    )
    return AgentService(ClaudeClient(), tools)


def get_listening_service() -> ListeningService:
    return ListeningService(
        MySQLListeningRepository(),
        storage_dir=settings.listening_audio_dir,
        transcribe_file=whisper_transcriber.transcribe_to_sentences,
        transcribe_clip=whisper_transcriber.transcribe_clip,
        max_upload_bytes=settings.listening_max_upload_mb * 1024 * 1024,
    )


# Opened dictionaries are cached for the life of the process (their key index is read once).
dictionary_files = DictionaryFiles(settings.dictionaries_dir)


def get_dictionary_library_service() -> DictionaryLibraryService:
    return DictionaryLibraryService(
        MySQLDictionaryRepository(),
        dictionary_files,
        secret=settings.jwt_secret,
        max_upload_bytes=settings.dictionary_max_upload_mb * 1024 * 1024,
    )


def get_word_explainer_service() -> WordExplainerService:
    # ClaudeClient is only built when a new explanation is generated (cached reads need no API key).
    return WordExplainerService(MySQLExplanationRepository(), model_factory=ClaudeClient)


def build_planner_tools(user_id: int, plan_date) -> PlannerTools:
    return PlannerTools(
        user_id=user_id,
        plan_date=plan_date,
        word_service=get_word_service(),
        review_service=get_review_service(),
        practice=MySQLPracticeRepository(),
        plans=MySQLStudyPlanRepository(),
        listening=MySQLListeningRepository(),
        model_name=settings.agent_model,
    )


def build_planner_service(user_id: int, plan_date) -> PlannerService:
    # The tools work without an API key; ClaudeClient is only created when a plan is generated.
    return PlannerService(ClaudeClient(), build_planner_tools(user_id, plan_date))
