from app.models.code_chunk import CodeChunk
from app.models.project import Project
from app.models.repository import Repository
from app.models.user import User
from app.services.repository_intelligence.vector_retrieval import (
    retrieve_similar_chunks,
)


def test_strong_semantic_match_is_retrieved(db_session):
    query_vector = [1.0] + [0.0] * 127

    user = User(
        email="vector-test@example.com",
        full_name="Vector Test User",
        hashed_password="test-password",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        name="Vector Retrieval Test Project",
        description="Test project for vector retrieval.",
        status="active",
        owner_id=user.id,
    )

    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    repository = Repository(
        name="Vector Retrieval Test Repository",
        url="https://example.com/vector-retrieval-test",
        default_branch="main",
        language="Python",
        status="ready",
        project_id=project.id,
    )

    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    chunk = CodeChunk(
        repository_id=repository.id,
        chunk_id="test-chunk-1",
        path="hello.py",
        content=(
            "def hello_world(name):\n"
            "    return 'Hello World'\n"
        ),
        chunk_type="function",
        symbol_name="hello_world",
        start_line=1,
        end_line=2,
        embedding=query_vector,
    )

    db_session.add(chunk)
    db_session.commit()

    class MatchingEmbeddingProvider:
        def embed_text(self, text: str) -> list[float]:
            return query_vector

    results = retrieve_similar_chunks(
        db=db_session,
        repository_id=repository.id,
        query="Where is the hello world function?",
        limit=3,
        embedding_provider=MatchingEmbeddingProvider(),
    )

    assert len(results) == 1
    assert results[0].path == "hello.py"
    assert results[0].symbol_name == "hello_world"
    assert results[0].distance == 0.0
    assert results[0].relevance_score >= 0.50

def test_semantic_match_is_not_rejected_by_code_specific_scoring(
    db_session,
):
    query_vector = [1.0] + [0.0] * 127

    user = User(
        email="vector-boundary-test@example.com",
        full_name="Vector Boundary Test User",
        hashed_password="test-password",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        name="Vector Boundary Test Project",
        description="Test project for semantic retrieval ranking.",
        status="active",
        owner_id=user.id,
    )

    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    repository = Repository(
        name="Vector Boundary Test Repository",
        url="https://example.com/vector-boundary-test",
        default_branch="main",
        language="Python",
        status="ready",
        project_id=project.id,
    )

    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    chunk = CodeChunk(
        repository_id=repository.id,
        chunk_id="boundary-test-chunk",
        path="hello.py",
        content=(
            "def hello_world(name):\n"
            "    return 'Hello World'\n"
        ),
        chunk_type="function",
        symbol_name="hello_world",
        start_line=1,
        end_line=2,
        embedding=query_vector,
    )

    db_session.add(chunk)
    db_session.commit()

    class MatchingEmbeddingProvider:
        def embed_text(self, text: str) -> list[float]:
            return query_vector

    results = retrieve_similar_chunks(
        db=db_session,
        repository_id=repository.id,
        query="Where is the hello world function?",
        limit=3,
        embedding_provider=MatchingEmbeddingProvider(),
        min_relevance_score=0.50,
    )

    assert len(results) == 1
    assert results[0].symbol_name == "hello_world"



def test_code_specific_query_prioritizes_relevant_symbol(db_session):
    query_vector = [1.0] + [0.0] * 127

    user = User(
        email="code-ranking-test@example.com",
        full_name="Code Ranking Test User",
        hashed_password="test-password",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        name="Code Ranking Test Project",
        description="Test project for code-aware ranking.",
        status="active",
        owner_id=user.id,
    )

    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    repository = Repository(
        name="Code Ranking Test Repository",
        url="https://example.com/code-ranking-test",
        default_branch="main",
        language="Python",
        status="ready",
        project_id=project.id,
    )

    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    relevant_chunk = CodeChunk(
        repository_id=repository.id,
        chunk_id="relevant-conflict-chunk",
        path="hotel/views.py",
        content=(
            "def room_has_booking_conflict(room, check_in, check_out):\n"
            "    bookings = Booking.objects.filter(\n"
            "        room=room,\n"
            "        status__in=['Confirmed', 'Completed'],\n"
            "        check_in__lt=check_out,\n"
            "        check_out__gt=check_in,\n"
            "    )\n"
            "    return bookings.exists()\n"
        ),
        chunk_type="function",
        symbol_name="room_has_booking_conflict",
        start_line=172,
        end_line=184,
        embedding=query_vector,
    )

    unrelated_chunk = CodeChunk(
        repository_id=repository.id,
        chunk_id="unrelated-chunk",
        path="hotel/models.py",
        content=(
            "class HotelSettings:\n"
            "    name = 'Luxury Grand Hotel'\n"
        ),
        chunk_type="class",
        symbol_name="HotelSettings",
        start_line=1,
        end_line=3,
        embedding=query_vector,
    )

    db_session.add_all(
        [
            relevant_chunk,
            unrelated_chunk,
        ]
    )
    db_session.commit()

    class MatchingEmbeddingProvider:
        def embed_text(self, text: str) -> list[float]:
            return query_vector

    results = retrieve_similar_chunks(
        db=db_session,
        repository_id=repository.id,
        query="How does the booking conflict check prevent overlapping reservations?",
        limit=2,
        embedding_provider=MatchingEmbeddingProvider(),
    )

    assert len(results) == 2
    assert results[0].symbol_name == "room_has_booking_conflict"
    assert results[0].relevance_score > results[1].relevance_score


def test_weak_semantic_match_is_filtered_by_max_distance(db_session):
    query_vector = [1.0] + [0.0] * 127
    weak_vector = [0.0] + [1.0] + [0.0] * 126

    user = User(
        email="distance-filter-test@example.com",
        full_name="Distance Filter Test User",
        hashed_password="test-password",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(
        name="Distance Filter Test Project",
        description="Test project for distance filtering.",
        status="active",
        owner_id=user.id,
    )

    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    repository = Repository(
        name="Distance Filter Test Repository",
        url="https://example.com/distance-filter-test",
        default_branch="main",
        language="Python",
        status="ready",
        project_id=project.id,
    )

    db_session.add(repository)
    db_session.commit()
    db_session.refresh(repository)

    chunk = CodeChunk(
        repository_id=repository.id,
        chunk_id="weak-distance-chunk",
        path="unrelated.py",
        content=(
            "def unrelated_function():\n"
            "    return 'This is unrelated code'\n"
        ),
        chunk_type="function",
        symbol_name="unrelated_function",
        start_line=1,
        end_line=2,
        embedding=weak_vector,
    )

    db_session.add(chunk)
    db_session.commit()

    class MatchingEmbeddingProvider:
        def embed_text(self, text: str) -> list[float]:
            return query_vector

    results = retrieve_similar_chunks(
        db=db_session,
        repository_id=repository.id,
        query="How does the booking conflict check prevent overlapping reservations?",
        limit=5,
        max_distance=0.50,
        embedding_provider=MatchingEmbeddingProvider(),
    )

    assert results == []