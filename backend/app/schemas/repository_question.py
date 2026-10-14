from pydantic import BaseModel


class RepositoryQuestionRequest(BaseModel):
    question: str


class RepositorySource(BaseModel):
    path: str
    symbol_name: str | None
    start_line: int | None
    end_line: int | None
    chunk_type: str
    relevance_score: float


class RepositoryQuestionResponse(BaseModel):
    repository_id: int
    question: str
    answer: str
    intent: str
    intent_confidence: float
    sources: list[RepositorySource]