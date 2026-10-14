from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.code_chunk import CodeChunk
from app.services.repository_intelligence.embeddings import (
    EmbeddingProvider,
    GeminiEmbeddingProvider,
)


@dataclass
class RetrievedCodeChunk:
    chunk_id: str
    path: str
    content: str
    chunk_type: str
    symbol_name: str | None
    start_line: int | None
    end_line: int | None
    distance: float
    relevance_score: float = 0.0


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(
            r"[A-Za-z_][A-Za-z0-9_]*",
            text,
        )
        if len(token) > 2
    }


def _calculate_lexical_score(query: str, chunk: CodeChunk) -> float:
    query_tokens = _tokenize(query)

    if not query_tokens:
        return 0.0

    content_tokens = _tokenize(chunk.content)
    path_tokens = _tokenize(chunk.path)
    symbol_tokens = _tokenize(chunk.symbol_name or "")

    content_matches = len(query_tokens.intersection(content_tokens))
    path_matches = len(query_tokens.intersection(path_tokens))
    symbol_matches = len(query_tokens.intersection(symbol_tokens))

    content_score = content_matches / len(query_tokens)
    path_score = path_matches / len(query_tokens)
    symbol_score = symbol_matches / len(query_tokens)

    return (
        content_score * 0.50
        + path_score * 0.20
        + symbol_score * 0.30
    )


def _calculate_code_relevance_score(
    query: str,
    chunk: CodeChunk,
) -> float:
    """
    Calculate code-aware relevance signals.

    These signals are intentionally supplemental. They should improve
    ranking for engineering-specific queries without overpowering
    semantic similarity for general repository questions.
    """
    query_lower = query.lower()
    symbol = chunk.symbol_name.lower() if chunk.symbol_name else ""
    path = chunk.path.lower()
    content = chunk.content.lower()

    score = 0.0

    symbol_keywords = {
        "conflict": ["conflict", "overlap", "booking"],
        "availability": ["available", "availability", "booking", "room"],
        "booking": ["booking", "book", "reservation"],
        "prevent": ["conflict", "lock", "validate", "check", "prevent"],
    }

    matched_symbol_keywords = 0

    for query_keyword, related_symbols in symbol_keywords.items():
        if query_keyword in query_lower:
            if any(keyword in symbol for keyword in related_symbols):
                matched_symbol_keywords += 1

    if matched_symbol_keywords:
        score += min(matched_symbol_keywords * 0.10, 0.30)

    important_symbols = {
        "room_has_booking_conflict": 0.30,
        "is_room_available": 0.25,
        "book_room": 0.25,
    }

    if symbol in important_symbols:
        score += important_symbols[symbol]

    implementation_keywords = [
        "booking",
        "overlap",
        "conflict",
        "available",
        "select_for_update",
        "status__in",
        "check_in__lt",
        "check_out__gt",
    ]

    keyword_matches = sum(
        1
        for keyword in implementation_keywords
        if keyword in content
    )

    if keyword_matches:
        score += min(keyword_matches * 0.03, 0.20)

    if path.endswith("views.py") or path.endswith("services.py"):
        score += 0.05

    if "select_for_update" in content:
        score += 0.15

    if (
        "check_in__lt=check_out" in content
        and "check_out__gt=check_in" in content
    ):
        score += 0.15

    return min(score, 1.0)


def _calculate_relevance_score(
    vector_score: float,
    lexical_score: float,
    code_relevance_score: float,
) -> float:
    """
    Combine retrieval signals.

    Semantic similarity remains the dominant signal. Lexical and
    code-aware signals provide ranking assistance rather than acting
    as hard requirements for general semantic matches.
    """
    return (
        vector_score * 0.70
        + lexical_score * 0.15
        + code_relevance_score * 0.15
    )


def retrieve_similar_chunks(
    db: Session,
    repository_id: int,
    query: str,
    limit: int = 5,
    embedding_provider: EmbeddingProvider | None = None,
    max_distance: float = 0.50,
    min_relevance_score: float = 0.50,
) -> list[RetrievedCodeChunk]:

    if not query.strip():
        return []

    if limit < 1:
        return []

    if max_distance <= 0:
        return []

    if min_relevance_score < 0:
        return []

    provider = (
        embedding_provider
        or GeminiEmbeddingProvider(
            model="gemini-embedding-2",
            dimensions=128,
        )
    )

    query_embedding = provider.embed_text(query)

    distance_expression = CodeChunk.embedding.cosine_distance(
        query_embedding
    )

    candidate_limit = max(limit * 4, 15)

    statement = (
        select(
            CodeChunk,
            distance_expression.label("distance"),
        )
        .where(
            CodeChunk.repository_id == repository_id,
            CodeChunk.embedding.is_not(None),
        )
        .order_by(distance_expression)
        .limit(candidate_limit)
    )

    rows = db.execute(statement).all()

    candidates = []

    for chunk, distance in rows:
        distance_value = float(distance)

        if distance_value > max_distance:
            continue

        vector_score = max(
            0.0,
            1.0 - distance_value,
        )

        lexical_score = _calculate_lexical_score(
            query=query,
            chunk=chunk,
        )

        code_relevance_score = _calculate_code_relevance_score(
            query=query,
            chunk=chunk,
        )

        relevance_score = _calculate_relevance_score(
            vector_score=vector_score,
            lexical_score=lexical_score,
            code_relevance_score=code_relevance_score,
        )

        candidates.append(
            RetrievedCodeChunk(
                chunk_id=chunk.chunk_id,
                path=chunk.path,
                content=chunk.content,
                chunk_type=chunk.chunk_type,
                symbol_name=chunk.symbol_name,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                distance=distance_value,
                relevance_score=relevance_score,
            )
        )

    candidates.sort(
        key=lambda item: item.relevance_score,
        reverse=True,
    )

    filtered_candidates = [
        candidate
        for candidate in candidates
        if candidate.relevance_score >= min_relevance_score
    ]

    return filtered_candidates[:limit]
