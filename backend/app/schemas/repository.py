from pydantic import BaseModel, ConfigDict, HttpUrl
from datetime import datetime

class RepositoryCreate(BaseModel):
    name: str
    url: HttpUrl
    default_branch: str = "main"
    language: str | None = None


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: HttpUrl
    default_branch: str
    language: str | None
    status: str
    workspace_id: str | None = None
    project_id: int
    created_at: datetime
    updated_at: datetime