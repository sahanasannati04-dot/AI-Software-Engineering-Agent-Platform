from typing import Any

from pydantic import BaseModel


class AgentQuestionRequest(BaseModel):
    question: str


class AgentToolStep(BaseModel):
    step: int
    tool_name: str
    arguments: dict[str, Any]
    result: Any


class AgentQuestionResponse(BaseModel):
    repository_id: int
    question: str
    answer: str
    intent: str
    intent_confidence: float
    steps: list[AgentToolStep]
