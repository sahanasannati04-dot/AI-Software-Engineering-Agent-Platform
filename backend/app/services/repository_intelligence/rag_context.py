from dataclasses import dataclass

from app.services.repository_intelligence.vector_retrieval import (
    RetrievedCodeChunk,
    retrieve_similar_chunks,
)


@dataclass
class RAGContext:
    query: str
    chunks: list[RetrievedCodeChunk]
    context_text: str


def build_rag_context(
    db,
    repository_id: int,
    query: str,
    limit: int = 5,
) -> RAGContext:
    """
    Retrieve relevant repository code and format it
    into context that can later be supplied to an LLM.
    """

    if not query.strip():
        return RAGContext(
            query=query,
            chunks=[],
            context_text="",
        )

    chunks = retrieve_similar_chunks(
        db=db,
        repository_id=repository_id,
        query=query,
        limit=limit,
    )

    context_sections = []

    for index, chunk in enumerate(chunks, start=1):
        location = chunk.path

        if chunk.start_line is not None:
            location += f":{chunk.start_line}"

            if chunk.end_line is not None:
                location += f"-{chunk.end_line}"

        symbol = chunk.symbol_name or "anonymous"

        section = (
            f"### Context {index}\n"
            f"File: {location}\n"
            f"Symbol: {symbol}\n"
            f"Relevance score: {chunk.relevance_score:.4f}\n"
            f"Vector distance: {chunk.distance:.6f}\n\n"
            f"```text\n"
            f"{chunk.content}\n"
            f"```\n"
        )

        context_sections.append(section)

    context_text = "\n".join(context_sections)

    return RAGContext(
        query=query,
        chunks=chunks,
        context_text=context_text,
    )