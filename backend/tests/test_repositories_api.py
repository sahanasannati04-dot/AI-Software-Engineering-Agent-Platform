from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.main import app


def create_fake_user():
    return SimpleNamespace(
        id=1,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
    )


def create_fake_project():
    return SimpleNamespace(
        id=1,
        owner_id=1,
    )


def create_fake_repository():
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    return SimpleNamespace(
        id=1,
        name="Test Repository",
        url="https://github.com/example/test-repository",
        default_branch="main",
        language="Python",
        project_id=1,
        status="pending",
        workspace_id=None,
        created_at=now,
        updated_at=now,
    )


def test_create_repository_queues_ingestion_job():
    fake_user = create_fake_user()
    fake_project = create_fake_project()
    fake_repository = create_fake_repository()

    fake_db = MagicMock()
    fake_db.scalar.return_value = fake_project

    def refresh_repository(repository):
        repository.id = fake_repository.id
        repository.created_at = fake_repository.created_at
        repository.updated_at = fake_repository.updated_at

    fake_db.refresh.side_effect = refresh_repository

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    try:
        with patch(
            "app.api.v1.repositories.enqueue_repository_ingestion",
            return_value="test-job-id",
        ) as mock_enqueue:
            client = TestClient(app)

            response = client.post(
                "/api/v1/repositories/1",
                json={
                    "name": "Test Repository",
                    "url": (
                        "https://github.com/example/"
                        "test-repository"
                    ),
                    "default_branch": "main",
                    "language": "Python",
                },
            )

        assert response.status_code == 201

        data = response.json()

        assert data["id"] == 1
        assert data["name"] == "Test Repository"
        assert data["url"] == (
            "https://github.com/example/test-repository"
        )
        assert data["default_branch"] == "main"
        assert data["language"] == "Python"
        assert data["status"] == "pending"
        assert data["project_id"] == 1
        assert data["workspace_id"] is None

        mock_enqueue.assert_called_once_with(
            repository_id=1,
        )

        fake_db.add.assert_called_once()

        created_repository = fake_db.add.call_args.args[0]

        assert created_repository.name == (
            "Test Repository"
        )
        assert created_repository.url == (
            "https://github.com/example/test-repository"
        )
        assert created_repository.default_branch == "main"
        assert created_repository.language == "Python"
        assert created_repository.project_id == 1
        assert created_repository.status == "pending"

        fake_db.commit.assert_called()

    finally:
        app.dependency_overrides.clear()


def test_create_repository_rejects_missing_project():
    fake_user = create_fake_user()

    fake_db = MagicMock()
    fake_db.scalar.return_value = None

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    try:
        with patch(
            "app.api.v1.repositories.enqueue_repository_ingestion"
        ) as mock_enqueue:
            client = TestClient(app)

            response = client.post(
                "/api/v1/repositories/999",
                json={
                    "name": "Test Repository",
                    "url": (
                        "https://github.com/example/"
                        "test-repository"
                    ),
                    "default_branch": "main",
                    "language": "Python",
                },
            )

        assert response.status_code == 404

        assert response.json()["detail"] == (
            "Project not found."
        )

        mock_enqueue.assert_not_called()

    finally:
        app.dependency_overrides.clear()


def test_create_repository_returns_503_when_queue_fails():
    fake_user = create_fake_user()
    fake_project = create_fake_project()
    fake_repository = create_fake_repository()

    fake_db = MagicMock()
    fake_db.scalar.return_value = fake_project
    fake_db.get.return_value = fake_repository

    def refresh_repository(repository):
        repository.id = fake_repository.id
        repository.created_at = fake_repository.created_at
        repository.updated_at = fake_repository.updated_at

    fake_db.refresh.side_effect = refresh_repository

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    try:
        with patch(
            "app.api.v1.repositories.enqueue_repository_ingestion",
            side_effect=RuntimeError(
                "Redis queue unavailable."
            ),
        ) as mock_enqueue:
            client = TestClient(app)

            response = client.post(
                "/api/v1/repositories/1",
                json={
                    "name": "Test Repository",
                    "url": (
                        "https://github.com/example/"
                        "test-repository"
                    ),
                    "default_branch": "main",
                    "language": "Python",
                },
            )

        assert response.status_code == 503

        assert "ingestion job could not be queued" in (
            response.json()["detail"]
        )

        mock_enqueue.assert_called_once_with(
            repository_id=1,
        )

    finally:
        app.dependency_overrides.clear()
