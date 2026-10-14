import pytest

from app.models.repository import Repository
from app.services.repository.repository_service import (
    RepositoryService,
    RepositoryStatusError,
)


def create_repository(status: str = "pending") -> Repository:
    return Repository(
        name="Test Repository",
        url="https://github.com/example/test-repository",
        default_branch="main",
        language="Python",
        status=status,
        project_id=1,
    )


def test_pending_can_transition_to_cloning():
    service = RepositoryService()
    repository = create_repository("pending")

    service.mark_cloning(repository)

    assert repository.status == "cloning"


def test_cloning_can_transition_to_connected():
    service = RepositoryService()
    repository = create_repository("cloning")

    service.mark_connected(repository)

    assert repository.status == "connected"


def test_connected_can_transition_to_analyzing():
    service = RepositoryService()
    repository = create_repository("connected")

    service.mark_analyzing(repository)

    assert repository.status == "analyzing"


def test_analyzing_can_transition_to_ready():
    service = RepositoryService()
    repository = create_repository("analyzing")

    service.mark_ready(repository)

    assert repository.status == "ready"


def test_any_active_state_can_transition_to_failed():
    service = RepositoryService()

    for status in (
        "pending",
        "cloning",
        "connected",
        "analyzing",
        "ready",
    ):
        repository = create_repository(status)

        service.mark_failed(repository)

        assert repository.status == "failed"


def test_failed_can_retry_from_pending():
    service = RepositoryService()
    repository = create_repository("failed")

    service.mark_pending(repository)

    assert repository.status == "pending"


def test_failed_can_retry_from_cloning():
    service = RepositoryService()
    repository = create_repository("failed")

    service.mark_cloning(repository)

    assert repository.status == "cloning"


def test_invalid_transition_raises_error():
    service = RepositoryService()
    repository = create_repository("pending")

    with pytest.raises(RepositoryStatusError):
        service.mark_ready(repository)


def test_invalid_status_raises_error():
    service = RepositoryService()
    repository = create_repository("pending")

    with pytest.raises(RepositoryStatusError):
        service.set_status(repository, "invalid")


def test_same_status_is_allowed():
    service = RepositoryService()
    repository = create_repository("ready")

    service.mark_ready(repository)

    assert repository.status == "ready"