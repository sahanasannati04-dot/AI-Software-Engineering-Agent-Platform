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


def create_fake_repository():
    return SimpleNamespace(
        id=1,
        project_id=1,
    )


def create_fake_db(repository):
    db = MagicMock()
    db.scalar.return_value = repository
    return db


def test_agent_question_api_returns_answer():
    fake_user = create_fake_user()
    fake_repository = create_fake_repository()
    fake_db = create_fake_db(fake_repository)

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    fake_result = {
        "answer": (
            "The booking conflict logic is implemented "
            "in hotel/views.py."
        ),
        "intent": "code_search",
        "intent_confidence": 0.95,
        "steps": [
            {
                "step": 1,
                "tool_name": "inspect_symbol",
                "arguments": {
                    "symbol_name": "room_has_booking_conflict",
                },
                "result": {
                    "path": "hotel/views.py",
                    "start_line": 172,
                    "end_line": 200,
                },
            }
        ],
    }

    try:
        with patch(
            "app.api.v1.agent_questions.answer_agent_question",
            return_value=fake_result,
        ) as mock_service:
            client = TestClient(app)

            response = client.post(
                "/api/v1/agent-questions/1/1",
                json={
                    "question": (
                        "Where is the booking conflict "
                        "logic implemented?"
                    )
                },
            )

        assert response.status_code == 200

        data = response.json()

        assert data["repository_id"] == 1

        assert data["question"] == (
            "Where is the booking conflict "
            "logic implemented?"
        )

        assert data["answer"] == (
            "The booking conflict logic is implemented "
            "in hotel/views.py."
        )

        assert data["intent"] == "code_search"
        assert data["intent_confidence"] == 0.95

        assert len(data["steps"]) == 1

        assert data["steps"][0]["step"] == 1

        assert (
            data["steps"][0]["tool_name"]
            == "inspect_symbol"
        )

        mock_service.assert_called_once_with(
            db=fake_db,
            repository_id=1,
            question=(
                "Where is the booking conflict "
                "logic implemented?"
            ),
            conversation_id=None,
            user_id=1,
        )

    finally:
        app.dependency_overrides.clear()


def test_agent_question_api_rejects_empty_question():
    fake_user = create_fake_user()
    fake_repository = create_fake_repository()
    fake_db = create_fake_db(fake_repository)

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    try:
        with patch(
            "app.api.v1.agent_questions.answer_agent_question"
        ) as mock_service:
            client = TestClient(app)

            response = client.post(
                "/api/v1/agent-questions/1/1",
                json={
                    "question": "   ",
                },
            )

        assert response.status_code == 400

        assert response.json()["detail"] == (
            "Question cannot be empty."
        )

        mock_service.assert_not_called()

    finally:
        app.dependency_overrides.clear()


def test_agent_question_api_rejects_missing_repository():
    fake_user = create_fake_user()
    fake_db = create_fake_db(None)

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    try:
        with patch(
            "app.api.v1.agent_questions.answer_agent_question"
        ) as mock_service:
            client = TestClient(app)

            response = client.post(
                "/api/v1/agent-questions/1/999",
                json={
                    "question": "Explain the repository."
                },
            )

        assert response.status_code == 404

        assert response.json()["detail"] == (
            "Repository not found."
        )

        mock_service.assert_not_called()

    finally:
        app.dependency_overrides.clear()


def test_agent_question_api_passes_conversation_id():
    fake_user = create_fake_user()
    fake_repository = create_fake_repository()
    fake_db = create_fake_db(fake_repository)

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    fake_result = {
        "answer": (
            "The function checks confirmed bookings."
        ),
        "intent": "code_explanation",
        "intent_confidence": 0.91,
        "steps": [],
    }

    try:
        with patch(
            "app.api.v1.agent_questions.answer_agent_question",
            return_value=fake_result,
        ) as mock_service:
            client = TestClient(app)

            response = client.post(
                "/api/v1/agent-questions/1/1"
                "?conversation_id=10",
                json={
                    "question": (
                        "Explain that function."
                    )
                },
            )

        assert response.status_code == 200

        data = response.json()

        assert data["repository_id"] == 1
        assert data["answer"] == (
            "The function checks confirmed bookings."
        )
        assert data["intent"] == "code_explanation"
        assert data["intent_confidence"] == 0.91
        assert data["steps"] == []

        mock_service.assert_called_once_with(
            db=fake_db,
            repository_id=1,
            question="Explain that function.",
            conversation_id=10,
            user_id=1,
        )

    finally:
        app.dependency_overrides.clear()

def test_agent_question_api_returns_503_on_runtime_error():
    fake_user = create_fake_user()
    fake_repository = create_fake_repository()
    fake_db = create_fake_db(fake_repository)

    app.dependency_overrides[get_current_user] = (
        lambda: fake_user
    )
    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    try:
        with patch(
            "app.api.v1.agent_questions.answer_agent_question",
            side_effect=RuntimeError(
                "Gemini API quota has been exhausted."
            ),
        ) as mock_service:
            client = TestClient(app)

            response = client.post(
                "/api/v1/agent-questions/1/1",
                json={
                    "question": (
                        "Explain the booking conflict logic."
                    )
                },
            )

        assert response.status_code == 503

        assert response.json() == {
            "detail": (
                "The AI engineering agent is temporarily "
                "unavailable. Please try again later."
            )
        }

        mock_service.assert_called_once_with(
            db=fake_db,
            repository_id=1,
            question=(
                "Explain the booking conflict logic."
            ),
            conversation_id=None,
            user_id=1,
        )

    finally:
        app.dependency_overrides.clear()