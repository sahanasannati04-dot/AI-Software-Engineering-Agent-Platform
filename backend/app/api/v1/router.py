from fastapi import APIRouter

from app.api.v1.agent_questions import router as agent_questions_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.health import router as health_router
from app.api.v1.projects import router as projects_router
from app.api.v1.repositories import router as repositories_router
from app.api.v1.repository_questions import (
    router as repository_questions_router,
)


api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(repositories_router)
api_router.include_router(repository_questions_router)
api_router.include_router(agent_questions_router)
api_router.include_router(conversations_router)
