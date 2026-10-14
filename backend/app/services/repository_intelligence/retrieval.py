from dataclasses import dataclass


@dataclass
class RetrievalResult:
    result_type: str
    name: str
    path: str
    line_number: int | None = None
    content: str | None = None
    score: float = 0.0

def convert_search_results(
    results: list[dict],
) -> list[RetrievalResult]:
    converted = []

    for result in results:
        result_type = result.get("type", "unknown")

        if result_type in {"class", "function"}:
            converted.append(
                RetrievalResult(
                    result_type=result_type,
                    name=result.get("name", ""),
                    path=result.get("path", ""),
                    content=None,
                )
            )

        elif result_type == "text":
            line = result.get("line", "")

            converted.append(
                RetrievalResult(
                    result_type="text",
                    name="",
                    path=result.get("path", ""),
                    line_number=result.get("line_number"),
                    content=line,
                )
            )

    return converted

def deduplicate_results(
    results: list[RetrievalResult],
) -> list[RetrievalResult]:
    seen = set()
    unique_results = []

    for result in results:
        if result.result_type in {"class", "function"}:
            key = (
                result.path,
                result.name,
            )

        else:
            key = (
                result.path,
                result.line_number,
                result.content,
            )

        if key in seen:
            continue

        seen.add(key)
        unique_results.append(result)

    return unique_results

def rank_results(
    results: list[RetrievalResult],
    query: str = "",
) -> list[RetrievalResult]:
    for result in results:
        if query:
            result.score = calculate_relevance_score(
                result,
                query,
            )
        else:
            if result.result_type == "function":
                result.score = 1.0

            elif result.result_type == "class":
                result.score = 0.9

            elif result.result_type == "text":
                result.score = 0.7

            else:
                result.score = 0.5

    return sorted(
        results,
        key=lambda result: result.score,
        reverse=True,
    )

def retrieve_code_context(
    search_results: list[dict],
    query: str = "",
    max_results: int = 10,
) -> list[RetrievalResult]:
    converted = convert_search_results(
        search_results
    )

    unique_results = deduplicate_results(
        converted
    )

    ranked_results = rank_results(
        unique_results,
        query,
    )

    return ranked_results[:max_results]

def calculate_relevance_score(
    result: RetrievalResult,
    query: str,
) -> float:
    query = query.strip().lower()

    if not query:
        return 0.0

    score = 0.0

    if result.name:
        name = result.name.lower()

        if name == query:
            score += 1.0

        elif query in name:
            score += 0.8

    if result.content:
        content = result.content.lower()

        if query in content:
            score += 0.6

    if result.result_type == "function":
        score += 0.2

    elif result.result_type == "class":
        score += 0.15

    elif result.result_type == "text":
        score += 0.1

    return score
